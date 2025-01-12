from enum import Enum
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

class EvaluationMetric(Enum):
    ANSWER_RELEVANCY = 1
    
evaluation_map = {
    EvaluationMetric.ANSWER_RELEVANCY : AnswerRelevancyMetric,
}

def get_evaluation(request,context, response, metrics):
    metric_input_list = []
    for metric in metrics:
        metric_input_list.append(
            evaluation_map[metric](
                threshold=0.7,
                model="gpt-3.5-turbo",
                include_reason=True
            )
        )

    test_case = LLMTestCase(
        input=request,
        actual_output=response,
    )
    evaluation_result = evaluate(
            test_cases= [test_case],
            metrics=metric_input_list,
            print_results = False,
            write_cache = False
        )
    metric_data = {
        evaluation_result.test_results[0].metrics_data[0].name:{
            "score" : evaluation_result.test_results[0].metrics_data[0].score,
            "reason": evaluation_result.test_results[0].metrics_data[0].reason,
        },
    }
    return metric_data