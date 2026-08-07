from services.template_loader import TemplateLoader


class HTMLBuilder:

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

            rows += f"""
<tr>

<td>{index}</td>

<td>{item['label']}</td>

<td>{item['ticket_number']}</td>

<td>{item['description']}</td>

</tr>
"""

        html = template.replace(
            "{{SPRINT_NAME}}",
            sprint_name
        )

        html = html.replace(
            "{{TABLE_ROWS}}",
            rows
        )

        return html