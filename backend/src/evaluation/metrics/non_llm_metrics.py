from typing import Dict, List, Union
from .base import BaseMetric
from .enums import NonLLMMetricType
from .utility import TextProcessing, TextSimilarity, TextStats

class NonLLMMetricEvaluator(BaseMetric):
    def __init__(self, metrics: List[NonLLMMetricType]):
        self.metrics = metrics
        self.text_processor = TextProcessing()
        self.text_similarity = TextSimilarity()
        self.text_stats = TextStats()
        self.metric_map = {
            NonLLMMetricType.CONTEXT_QUERY_MATCH: self._calculate_context_query_match,
            NonLLMMetricType.ANSWER_COVERAGE: self._calculate_answer_coverage,
            NonLLMMetricType.RESPONSE_CONSISTENCY: self._calculate_response_consistency,
            NonLLMMetricType.INFORMATION_DENSITY: self._calculate_information_density,
            NonLLMMetricType.SOURCE_DIVERSITY: self._calculate_source_diversity
        }

    def evaluate(self, request: str, contexts: List[str], response: str) -> Dict[str, Dict[str, Union[float, str]]]:
        """Evaluates non-llm metrics using request, contexts and the reponse by LLM

        Args:
            query: User question
            contexts: List of retrieved contexts
            response: Generated response

        Returns:
            Dict[str, Dict[str, Union[float, str]]]: evals dict
        """
        results = {}

        for metric in self.metrics:
            score = self.metric_map[metric](request, contexts, response)
            results[metric.value] = {
                "score": score,
                "reason": self._get_reason(metric, score)
            }

        return results

    def _calculate_context_query_match(self, query: str, contexts: List[str], response:str) -> float:
        """
        Calculate how well contexts match the query
        
        Args:
            query: User question
            contexts: List of retrieved contexts
            response: Generated response
        Returns:
            Match score between 0 and 1
        """
        if not contexts:
            return 0.0
            
        query_terms = self.text_processor.tokenize_and_clean(query)
        if not query_terms:
            return 0.0
            
        scores = []
        for context in contexts:
            context_terms = self.text_processor.tokenize_and_clean(context)
            if context_terms:
                score = self.text_similarity.calculate_overlap_score(query_terms, context_terms)
                scores.append(score)
                
        return sum(scores) / len(contexts) if scores else 0.0
    
    def _calculate_answer_coverage(self, query:str, contexts: List[str], response: str) -> float:
        """
        Calculate what percentage of contexts are used in the response
        
        Args:
            query: User question
            contexts: List of retrieved contexts
            response: Generated response
        Returns:
            Coverage score between 0 and 1
        """
        if not contexts or not response:
            return 0.0
            
        covered_contexts = 0
        response_lower = response.lower()
        
        for context in contexts:
            context_phrases = [p.strip() for p in context.lower().split('.') 
                             if len(p.strip()) > 10]
            
            for phrase in context_phrases:
                if self.text_processor.is_substring_match(phrase, response_lower):
                    covered_contexts += 1
                    break
                    
        return covered_contexts / len(contexts)
    
    def _calculate_response_consistency(self, query:str, contexts: List[str], response: str) -> float:
        """
        Calculate how consistent the response is with contexts
        
        Args:
            query: User question
            contexts: List of retrieved contexts
            response: Generated response
        Returns:
            Consistency score between 0 and 1
        """
        if not contexts or not response:
            return 0.0
            
        response_facts = self.text_processor.extract_facts(response)
        if not response_facts:
            return 0.0
            
        consistent_facts = 0
        for fact in response_facts:
            fact_words = self.text_processor.tokenize_and_clean(fact)
            for context in contexts:
                context_words = self.text_processor.tokenize_and_clean(context)
                if self.text_similarity.calculate_overlap_score(fact_words, context_words) > 0.7:
                    consistent_facts += 1
                    break
                    
        return consistent_facts / len(response_facts)
    
    def _calculate_information_density(self, query:str, contexts: List[str], response: str) -> float:
        """
        Calculate ratio of factual content to response length
        
        Args:
            query: User question
            contexts: List of retrieved contexts
            response: Generated response
            
        Returns:
            Density score between 0 and 1
        """
        if not response:
            return 0.0
            
        facts = self.text_processor.extract_facts(response)
        if not facts:
            return 0.0
            
        fact_words = sum(self.text_stats.word_count(fact) for fact in facts)
        total_words = self.text_stats.word_count(response)
        
        return fact_words / total_words if total_words > 0 else 0.0
    
    def _calculate_source_diversity(self, query:str, contexts: List[str], response: str) -> float:
        """
        Calculate how many different contexts contribute to the response
        
        Args:
            response: Generated response
            contexts: List of retrieved contexts
            
        Returns:
            Diversity score between 0 and 1
        """
        if not contexts or not response:
            return 0.0
            
        response_lower = response.lower()
        unique_sources = set()
        
        for i, context in enumerate(contexts):
            context_phrases = [p.strip() for p in context.lower().split('.') 
                             if len(p.strip()) > 10]
            
            for phrase in context_phrases:
                if self.text_processor.is_substring_match(phrase, response_lower):
                    unique_sources.add(i)
                    break
                    
        return len(unique_sources) / len(contexts)

    def _get_reason(self, metric: NonLLMMetricType, score: float) -> str:
        # Provide human-readable explanations for scores
        reason_map = {
            NonLLMMetricType.CONTEXT_QUERY_MATCH: 
                f"Context matches {score:.1%} of query terms",
            NonLLMMetricType.ANSWER_COVERAGE:
                f"Response uses information from {score:.1%} of available contexts",
            NonLLMMetricType.RESPONSE_CONSISTENCY:
                f"Response is {score:.1%} consistent with provided contexts",
            NonLLMMetricType.INFORMATION_DENSITY:
                f"{score:.1%} of response content is factual information",
            NonLLMMetricType.SOURCE_DIVERSITY:
                f"Response draws from {score:.1%} of available sources"
        }
        return reason_map[metric]