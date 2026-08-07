"""
Singleton wrapper around the local Hugging Face model.
"""

import torch

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM
)

import config


class LocalLLM:

    _instance = None

    def __new__(cls):

        if cls._instance is None:

            cls._instance = super().__new__(cls)

            cls._instance._load_model()

        return cls._instance

    def _load_model(self):

        print("\nLoading Local LLM...\n")

        self.tokenizer = AutoTokenizer.from_pretrained(
            config.MODEL_NAME
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            config.MODEL_NAME,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        )

        print("Model Loaded.\n")

    def generate(
        self,
        system_prompt,
        user_prompt,
        max_tokens=512
    ):

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = self.tokenizer(
            text,
            return_tensors="pt"
        )

        inputs = {
            k: v.to(self.model.device)
            for k, v in inputs.items()
        }

        with torch.no_grad():

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.2,
                do_sample=False
            )

        generated = outputs[0][inputs["input_ids"].shape[1]:]

        return self.tokenizer.decode(
            generated,
            skip_special_tokens=True
        ).strip()