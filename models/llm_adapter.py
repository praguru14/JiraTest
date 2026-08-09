"""Simple adapter that exposes `generate()` and delegates to LocalLLM.

This keeps a small, thread-safe wrapper around the existing `LocalLLM`.
"""

import threading
import os

from .local_llm import LocalLLM
from .remote_llm import RemoteLLM


class LLMAdapter:

    def __init__(self):

        self._lock = threading.Lock()

        provider = os.getenv("LLM_PROVIDER", "local").lower()

        if provider == "remote":
            self._impl = RemoteLLM()
        else:
            self._impl = LocalLLM()

    def generate(self, system_prompt, user_prompt, max_tokens=512):
        with self._lock:
            return self._impl.generate(
                system_prompt,
                user_prompt,
                max_tokens=max_tokens
            )
