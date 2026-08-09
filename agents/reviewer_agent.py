import json

from models.llm_adapter import LLMAdapter
from services.prompt_loader import PromptLoader
import logging

logger = logging.getLogger("jira_conf.reviewer")


class ReviewerAgent:

    def __init__(self):

        self.llm = LLMAdapter()

        self.system_prompt = PromptLoader.load("reviewer_prompt.txt")

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

        try:
            return json.loads(response)
        except Exception as e:
            # attempt to find a JSON object or array inside the text
            text = response or ""
            start_obj = text.find("{")
            end_obj = text.rfind("}")
            start_arr = text.find("[")
            end_arr = text.rfind("]")

            candidate = None
            if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
                candidate = text[start_obj:end_obj+1]
            elif start_arr != -1 and end_arr != -1 and end_arr > start_arr:
                candidate = text[start_arr:end_arr+1]

            if candidate:
                try:
                    return json.loads(candidate)
                except Exception:
                    logger.warning("Failed to parse candidate JSON from reviewer response")
                    pass

            # final fallback: return a dict describing the parse failure
            logger.error("Reviewer JSON parse error", exc_info=True)
            return {
                "approved": False,
                "review_error": "json_parse_error",
                "raw": text,
                "exception": str(e)
            }