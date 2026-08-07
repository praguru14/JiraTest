import json

from models.local_llm import LocalLLM
from services.prompt_loader import PromptLoader
from services.jira_formatter import JiraFormatter
from services.json_service import JsonService


class ReleaseAgent:

    def __init__(self):

        self.llm = LocalLLM()

        self.system_prompt = PromptLoader.load(
            "release_prompt.txt"
        )

    def generate_release_notes(self, issues):

        release_notes = []

        print(f"\nGenerating release notes for {len(issues)} tickets...\n")

        for issue in issues:

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

            response = self.llm.generate(
                self.system_prompt,
                user_prompt
            )

            try:

                note = JsonService.parse_llm_json(response)

                release_notes.append(note)

            except Exception:

                print(f"Failed to parse {issue.key}")

                print(response)

        return release_notes