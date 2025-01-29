from enum import Enum

class LLMMetricType(Enum):
    ANSWER_RELEVANCY = "answer_relevancy"
    FAITHFULNESS = "faithfulness"
    CONTEXT_RELEVANCY = "context_relevancy"

class NonLLMMetricType(Enum):
    CONTEXT_QUERY_MATCH = "context_query_match"
    ANSWER_COVERAGE = "answer_coverage"
    RESPONSE_CONSISTENCY = "response_consistency"
    INFORMATION_DENSITY = "information_density"
    SOURCE_DIVERSITY = "source_diversity"