from pathlib import Path


class PromptLoader:

    @staticmethod
    def load(file_name):

        file = Path("prompts") / file_name

        return file.read_text(
            encoding="utf-8"
        )