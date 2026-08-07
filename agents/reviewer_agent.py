import json

from models.local_llm import LocalLLM
from services.prompt_loader import PromptLoader


class ReviewerAgent:

    def __init__(self):

        self.llm = LocalLLM()

        self.system_prompt = PromptLoader.load(
            "reviewer_prompt.txt"
        )

    def review(
        self,
        release_notes
    ):

        user_prompt = json.dumps(
            release_notes,
            indent=2
        )

        response = self.llm.generate(

            self.system_prompt,

            user_prompt

        )

        return json.loads(response)