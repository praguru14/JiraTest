import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.document_profile import DocumentProfile
from core.work_item import WorkItem
from models.llm_adapter import LLMAdapter
from services.json_service import JsonService
from services.prompt_loader import PromptLoader
from sources.jira_source import JiraWorkItemSource

logger = logging.getLogger("jira_conf.content_generator")


class ContentGenerator:
    """Generates structured content from normalized work items."""

    def __init__(self, profile: DocumentProfile, llm=None):
        self.profile = profile
        self.llm = llm or LLMAdapter()
        self.system_prompt = PromptLoader.load(profile.prompt_file)

    def generate(self, items):
        print(f"\nGenerating {self.profile.name} for {len(items)} items...\n")

        def process(item):
            work_item = self._coerce_work_item(item)
            logger.info("Processing %s", work_item.id)
            print(f"Processing {work_item.id}")
            user_prompt = self._build_prompt(work_item)

            for attempt in range(3):
                response = self.llm.generate(self.system_prompt, user_prompt)
                try:
                    content = JsonService.parse_llm_json(response)
                    if isinstance(content, dict) and not content.get("description"):
                        content["description"] = self.profile.fallback_description(work_item)
                    if self._is_valid(content):
                        return content
                except Exception:
                    pass

                logger.warning("Failed to parse %s (attempt %s)", work_item.id, attempt + 1)
                print(f"Failed to parse {work_item.id} (attempt {attempt + 1})")

            logger.error("Max attempts exceeded for %s", work_item.id)
            return None

        results = []
        max_workers = min(8, max(1, len(items)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process, item) for item in items]
            for future in as_completed(futures):
                content = future.result()
                if content:
                    results.append(content)
        return results

    def _build_prompt(self, item: WorkItem):
        return f"""
Ticket Number: {item.id}

Issue Type: {item.kind}

Summary: {item.title}

Labels: {", ".join(item.labels)}

Priority: {item.priority}

Description:
{item.description}
"""

    def _is_valid(self, content):
        if not isinstance(content, dict):
            return False
        if any(field not in content or not content[field] for field in self.profile.required_fields):
            return False
        label = content.get("label")
        return not (label is not None and (not isinstance(label, str) or not label.strip()))

    @staticmethod
    def _coerce_work_item(item):
        if isinstance(item, WorkItem):
            return item
        return JiraWorkItemSource.from_issue(item)
