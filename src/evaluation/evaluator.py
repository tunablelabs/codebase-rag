from typing import Dict, List, Union
from evaluation.metrics.enums import LLMMetricType, NonLLMMetricType
from evaluation.metrics.llm_metrics import LLMMetricEvaluator
from evaluation.metrics.non_llm_metrics import NonLLMMetricEvaluator

class Evaluator:
    def __init__(
        self,
        llm_metrics: List[LLMMetricType] = None,
        non_llm_metrics: List[NonLLMMetricType] = None,
        llm_threshold: float = 0.7,
        llm_model: str = "gpt-4o"
    ):
        self.llm_metrics = llm_metrics
        self.non_llm_metrics = non_llm_metrics
        self.llm_threshold = llm_threshold
        self.llm_model = llm_model

    def evaluate(
        self,
        use_llm: bool,
        request: str,
        contexts: List[str],
        response: str
    ) -> Dict[str, Dict[str, Union[float, str]]]:
        """
        Evaluate LLM system using configured metrics

        Args:
            request: User query
            context: Retrieved context
            response: Generated response

        Returns:
            Dictionary containing evaluation results for each metric
        """
        evaluators = []
        if use_llm and self.llm_metrics:
            evaluators.append(
                LLMMetricEvaluator(self.llm_metrics, self.llm_threshold, self.llm_model)
            )

        if self.non_llm_metrics:
            evaluators.append(
                NonLLMMetricEvaluator(self.non_llm_metrics)
            )
            
        results = {}
        for evaluator in evaluators:
            results.update(
                evaluator.evaluate(request, contexts, response)
            )
        return results