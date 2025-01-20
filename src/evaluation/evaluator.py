from typing import Dict, List, Union
from evaluation.metrics.enums import LLMMetricType, NonLLMMetricType
from evaluation.metrics.llm_metrics import LLMMetricEvaluator
from evaluation.metrics.non_llm_metrics import NonLLMMetricEvaluator

class Evaluator:
    def __init__(
        self,
        use_llm: bool = False,
        llm_metrics: List[LLMMetricType] = None,
        non_llm_metrics: List[NonLLMMetricType] = None,
        llm_threshold: float = 0.7,
        llm_model: str = "gpt-3.5-turbo"
    ):
        self.use_llm = use_llm
        self.evaluators = []

        if use_llm and llm_metrics:
            self.evaluators.append(
                LLMMetricEvaluator(llm_metrics, llm_threshold, llm_model)
            )

        if non_llm_metrics:
            self.evaluators.append(
                NonLLMMetricEvaluator(non_llm_metrics)
            )

    def evaluate(
        self,
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
        results = {}
        for evaluator in self.evaluators:
            results.update(
                evaluator.evaluate(request, contexts, response)
            )
        return results