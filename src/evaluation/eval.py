from enum import Enum
from typing import List, Dict, Union
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, ContextualRelevancyMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

class EvaluationMetric(Enum):
    ANSWER_RELEVANCY = 1
    FAITHFULNESS = 2
    CONTEXT_RELEVANCY = 3

class Evaluation:
    _evaluation_map = {
        EvaluationMetric.ANSWER_RELEVANCY: AnswerRelevancyMetric,
        EvaluationMetric.FAITHFULNESS: FaithfulnessMetric,
        EvaluationMetric.CONTEXT_RELEVANCY: ContextualRelevancyMetric,
    }

    @staticmethod
    def get_evaluation(request:str , context: str, response: str, metrics:  List[EvaluationMetric]) -> Dict[str,Dict[str,Union[str,int]]]:
        """Evaluate request, response & context for the given list of metrics

        Args:
            request (str): query request made to LLM
            context (str): context fetched for given request 
            response (str): query response from LLM
            metrics (List[EvaluationMetric]): List of different metrics

        Returns:
            Dict[str,Dict[str,Union[str,int]]]: Dict of metrics output containing score and reason
        """
        metric_input_list = []
        for metric in metrics:
            metric_input_list.append(
                Evaluation._evaluation_map[metric](
                    threshold=0.7,
                    model="gpt-3.5-turbo",
                    include_reason=True
                )
            )

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
        metric_data = {}
        for metric in evaluation_result.test_results[0].metrics_data:
            metric_data[metric.name] = {
                "score": metric.score,
                "reason": metric.reason,
            }
        return metric_data