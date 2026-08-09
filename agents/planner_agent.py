import json

from models.llm_adapter import LLMAdapter
from services.prompt_loader import PromptLoader
import logging

logger = logging.getLogger("jira_conf.planner")


class PlannerAgent:

    def __init__(self):

        self.llm = LLMAdapter()

        self.system_prompt = PromptLoader.load("planner_prompt.txt")

    def next_action(
        self,
        context
    ):

        response = self.llm.generate(

            self.system_prompt,

            json.dumps(context)

        )

        try:
            parsed = json.loads(response)
            logger.debug(f"Planner response: {parsed}")
            return parsed
        except Exception:
            logger.warning("Planner returned non-JSON response", exc_info=True)
            # fallback: return a FINISH decision
            return {"action": "FINISH"}