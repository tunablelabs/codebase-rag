from abc import ABC, abstractmethod
from typing import Dict, Union, List

class BaseMetric(ABC):
    @abstractmethod
    def evaluate(self, request: str, context: str, response: str) -> Dict[str, Union[float, str]]:
        pass