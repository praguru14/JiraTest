import json

from models.local_llm import LocalLLM
from services.prompt_loader import PromptLoader


class PlannerAgent:

    def __init__(self):

        self.llm = LocalLLM()

        self.system_prompt = PromptLoader.load(
            "planner_prompt.txt"
        )

    def next_action(
        self,
        context
    ):

        response = self.llm.generate(

            self.system_prompt,

            json.dumps(context)

        )

        return json.loads(response)