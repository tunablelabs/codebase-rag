from abc import ABC, abstractmethod
from typing import Iterator, Any

class BaseLLMProvider(ABC):
    @abstractmethod
    def prepare_client(self):
        pass

    @abstractmethod
    def invoke(self, messages: list[dict], temperature: float, **kwargs) -> dict:
        pass

    @abstractmethod
    def stream(self, messages: list[dict], temperature: float, **kwargs) -> Iterator[Any]:
        pass