from pathlib import Path


class TemplateLoader:

    @staticmethod
    def load(template_name: str) -> str:

        path = Path("templates") / template_name

        return path.read_text(
            encoding="utf-8"
        )