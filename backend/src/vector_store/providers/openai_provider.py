import requests
import json
from typing import Iterator, Any
from .base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def prepare_client(self):
        pass  # Empty implementation since we're using REST API

    def invoke(self, messages: list[dict], temperature: float, **kwargs) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        response = requests.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def stream(self, messages: list[dict], temperature: float, **kwargs) -> Iterator[Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        with requests.post(self.base_url, headers=headers, json=payload, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    chunk = line.decode("utf-8").strip()
                    if chunk.startswith("data: "):
                        chunk = chunk[6:]
                        if chunk != "[DONE]":
                            try:
                                chunk_data = json.loads(chunk)
                                yield chunk_data
                            except json.JSONDecodeError:
                                continue