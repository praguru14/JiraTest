import os
import requests


class RemoteLLM:

    def __init__(self):

        self.api_url = os.getenv("HF_API_URL")
        self.api_token = os.getenv("HF_API_TOKEN")

        if not self.api_url or not self.api_token:
            raise RuntimeError("HF_API_URL and HF_API_TOKEN must be set for RemoteLLM")

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def generate(self, system_prompt, user_prompt, max_tokens=512):

        payload = {
            "inputs": system_prompt + "\n" + user_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.2
            }
        }

        resp = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)

        resp.raise_for_status()

        data = resp.json()

        if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()

        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"].strip()

        return str(data)
