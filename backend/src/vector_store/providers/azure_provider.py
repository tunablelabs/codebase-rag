import requests
import json
from typing import Iterator, Any
from .base import BaseLLMProvider

class AzureOpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, endpoint: str, deployment_name: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment_name = deployment_name

    def prepare_client(self):
        pass  # Empty implementation since we're using REST API

    def invoke(self, messages: list[dict], temperature: float, **kwargs) -> dict:
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        
        url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version=2024-02-15-preview"
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def stream(self, messages: list[dict], temperature: float, **kwargs) -> Iterator[Any]:
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        
        url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version=2024-02-15-preview"
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        with requests.post(url, headers=headers, json=payload, stream=True) as response:
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