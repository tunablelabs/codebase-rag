import requests
import json
from typing import Iterator, Any
from .base import BaseLLMProvider

class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/messages"

    def prepare_client(self):
        pass

    def _convert_to_claude_format(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI format messages to Claude format"""
        claude_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                # Add system message as user message with special prefix
                claude_messages.append({
                    "role": "user",
                    "content": f"System instruction: {msg['content']}"
                })
            elif role == "assistant":
                claude_messages.append({
                    "role": "assistant",
                    "content": msg["content"]
                })
            elif role == "user":
                claude_messages.append({
                    "role": "user",
                    "content": msg["content"]
                })
        return claude_messages

    def invoke(self, messages: list[dict], temperature: float, **kwargs) -> dict:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        claude_messages = self._convert_to_claude_format(messages)
        
        payload = {
            "model": self.model,
            "messages": claude_messages,
            "temperature": temperature,
            **kwargs,
        }

        response = requests.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Convert Claude response to OpenAI format
        claude_response = response.json()
        return {
            "choices": [{
                "message": {
                    "content": claude_response["content"][0]["text"],
                    "role": "assistant"
                }
            }],
            "usage": {
                "completion_tokens": claude_response.get("usage", {}).get("output_tokens", 0),
                "prompt_tokens": claude_response.get("usage", {}).get("input_tokens", 0),
                "total_tokens": (
                    claude_response.get("usage", {}).get("output_tokens", 0) +
                    claude_response.get("usage", {}).get("input_tokens", 0)
                )
            }
        }

    def stream(self, messages: list[dict], temperature: float, **kwargs) -> Iterator[Any]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        claude_messages = self._convert_to_claude_format(messages)
        
        payload = {
            "model": self.model,
            "messages": claude_messages,
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
                                event_data = json.loads(chunk)
                                # Convert Claude stream format to OpenAI format
                                yield {
                                    "choices": [{
                                        "delta": {
                                            "content": event_data.get("delta", {}).get("text", ""),
                                        }
                                    }]
                                }
                            except json.JSONDecodeError:
                                continue