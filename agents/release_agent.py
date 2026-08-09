import json

from models.llm_adapter import LLMAdapter
from services.prompt_loader import PromptLoader
from services.jira_formatter import JiraFormatter
from services.json_service import JsonService
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger("jira_conf.release_agent")


class ReleaseAgent:

    def __init__(self):

        self.llm = LLMAdapter()

        self.system_prompt = PromptLoader.load("release_prompt.txt")

        self.allowed_labels = {
            "Feature",
            "Bug Fix",
            "Improvement",
            "Security"
        }

    def generate_release_notes(self, issues):

        release_notes = []

        print(f"\nGenerating release notes for {len(issues)} tickets...\n")

        def _process(issue):

            logger.info(f"Processing {issue.key}")
            print(f"Processing {issue.key}")

            description = JiraFormatter.get_description(issue)

            labels = ", ".join(issue.fields.labels)

            priority = (
                issue.fields.priority.name
                if issue.fields.priority
                else "None"
            )

            issue_type = (
                issue.fields.issuetype.name
                if issue.fields.issuetype
                else "Unknown"
            )

            summary = (
                issue.fields.summary
                if issue.fields.summary
                else ""
            )

            user_prompt = f"""
Ticket Number: {issue.key}

Issue Type: {issue_type}

Summary: {summary}

Labels: {labels}

Priority: {priority}

Description:
{description}
"""

            attempts = 0
            max_attempts = 2

            while attempts <= max_attempts:

                response = self.llm.generate(
                    self.system_prompt,
                    user_prompt
                )

                try:

                    note = JsonService.parse_llm_json(response)

                    if not self._validate_note(note):
                        raise ValueError("Validation failed")

                    return note

                except Exception:

                    attempts += 1

                    logger.warning(f"Failed to parse {issue.key} (attempt {attempts})")
                    print(f"Failed to parse {issue.key} (attempt {attempts})")

                    if attempts > max_attempts:
                        logger.error(f"Max attempts exceeded for {issue.key}; response={response}")
                        print(response)
                        return None

                    print("Retrying...")

        max_workers = min(8, max(1, len(issues)))

        with ThreadPoolExecutor(max_workers=max_workers) as ex:

            futures = {ex.submit(_process, issue): issue for issue in issues}

            for fut in as_completed(futures):

                note = fut.result()

                if note:
                    release_notes.append(note)

        return release_notes

    def _validate_note(self, note):

        if not isinstance(note, dict):
            return False

        if "label" not in note or "ticket_number" not in note or "description" not in note:
            return False

        if note["label"] not in self.allowed_labels:
            return False

        return True