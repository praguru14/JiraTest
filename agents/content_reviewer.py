import json
import logging

from core.document_profile import DocumentProfile
from models.llm_adapter import LLMAdapter
from services.prompt_loader import PromptLoader

logger = logging.getLogger("jira_conf.content_reviewer")


class ContentReviewer:
    """Reviews generated content using the active document profile."""

    def __init__(self, profile: DocumentProfile, llm=None):
        self.profile = profile
        self.llm = llm or LLMAdapter()
        self.system_prompt = PromptLoader.load(profile.review_prompt_file)

    def review(self, content):
        response = self.llm.generate(
            self.system_prompt,
            json.dumps(content, indent=2),
        )
        try:
            return json.loads(response)
        except Exception as exc:
            candidate = self._extract_json(response or "")
            if candidate is not None:
                try:
                    return json.loads(candidate)
                except Exception:
                    logger.warning("Failed to parse reviewer JSON candidate")
            logger.error("Reviewer JSON parse error", exc_info=True)
            return {
                "approved": False,
                "review_error": "json_parse_error",
                "raw": response or "",
                "exception": str(exc),
            }

    @staticmethod
    def _extract_json(text):
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        if start_obj != -1 and end_obj > start_obj:
            return text[start_obj:end_obj + 1]
        start_arr = text.find("[")
        end_arr = text.rfind("]")
        if start_arr != -1 and end_arr > start_arr:
            return text[start_arr:end_arr + 1]
        return None
