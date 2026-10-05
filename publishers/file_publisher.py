from pathlib import Path

from core.document import Document
from publishers.base import Publisher


class FilePublisher(Publisher):
    """Writes a rendered document to a local file."""

    def __init__(self, output_path):
        self.output_path = Path(output_path)

    def exists(self, title: str) -> bool:
        return self.output_path.exists()

    def count_items(self, title: str) -> int:
        if not self.output_path.exists():
            return 0
        rows = self.output_path.read_text(encoding="utf-8").count("<tr>")
        return max(0, rows - 1)

    def publish(self, document: Document) -> bool:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(document.body, encoding="utf-8")
        return True
