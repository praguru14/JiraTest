import os

import requests


class OllamaLLM:
    """Ollama client implementing the shared LLM interface."""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self.api_url = f"{self.base_url}/api/chat"
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    def generate(self, system_prompt, user_prompt, max_tokens=512):
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": 0.2,
                "num_predict": max_tokens,
            },
        }

        response = requests.post(self.api_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()

        try:
            return data["message"]["content"].strip()
        except (KeyError, TypeError) as exc:
            raise RuntimeError(f"Ollama returned an unexpected response: {data}") from exc