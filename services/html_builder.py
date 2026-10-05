from html import escape

import config

from services.template_loader import TemplateLoader
from core.document import Document


class HTMLBuilder:

    @staticmethod
    def build_document(sprint_name, release_notes):
        return Document(
            title=f"Release_Note_{sprint_name}",
            body=HTMLBuilder.build(sprint_name, release_notes),
            format="html",
            metadata={"document_type": "release_notes", "scope": sprint_name},
        )

    @staticmethod
    def build(
        sprint_name,
        release_notes
    ):

        template = TemplateLoader.load(
            "release_notes.html"
        )

        rows = ""

        for index, item in enumerate(
            release_notes,
            start=1
        ):

            ticket_number = str(item["ticket_number"])
            ticket_cell = HTMLBuilder._ticket_link(ticket_number)

            rows += f"""
<tr>

<td>{index}</td>

<td>{escape(str(item['label']))}</td>

<td>{ticket_cell}</td>

<td>{escape(str(item['description']))}</td>

</tr>
"""

        html = template.replace(
            "{{SPRINT_NAME}}",
            escape(str(sprint_name))
        )

        html = html.replace(
            "{{TABLE_ROWS}}",
            rows
        )

        return html

    @staticmethod
    def _ticket_link(ticket_number):
        label = escape(ticket_number)
        jira_url = getattr(config, "JIRA_URL", None)
        if not jira_url:
            return label

        href = f"{jira_url.rstrip('/')}/browse/{ticket_number}"
        return f'<a href="{escape(href, quote=True)}">{label}</a>'