from typing import Dict, List, Union
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, ContextualRelevancyMetric
from deepeval.test_case import LLMTestCase
from .base import BaseMetric
from .enums import LLMMetricType

class LLMMetricEvaluator(BaseMetric):
    def __init__(self, metrics: List[LLMMetricType], threshold: float = 0.7, model: str = "gpt-3.5-turbo"):
        self.metrics = metrics
        self.threshold = threshold
        self.model = model
        self.metric_map = {
            LLMMetricType.ANSWER_RELEVANCY: AnswerRelevancyMetric,
            LLMMetricType.FAITHFULNESS: FaithfulnessMetric,
            LLMMetricType.CONTEXT_RELEVANCY: ContextualRelevancyMetric,
        }

    def evaluate(self, request: str, context:List[str], response: str) -> Dict[str, Dict[str, Union[float, str]]]:
        """Evaluates llm metrics using request, contexts and the reponse by LLM

        Args:
            query: User question
            contexts: List of retrieved contexts
            response: Generated response

        Returns:
            Dict[str, Dict[str, Union[float, str]]]: evals dict
        """
        metric_input_list = [
            self.metric_map[metric](
                threshold=self.threshold,
                model=self.model,
                include_reason=True
            )
            for metric in self.metrics
        ]

        test_case = LLMTestCase(
            input=request,
            actual_output=response,
            retrieval_context=context
        )

        evaluation_result = evaluate(
            test_cases=[test_case],
            metrics=metric_input_list,
            print_results=False,
            write_cache=False
        )

        return {
            metric.name: {
                "score": metric.score,
                "reason": metric.reason,
            }
            for metric in evaluation_result.test_results[0].metrics_data
        }