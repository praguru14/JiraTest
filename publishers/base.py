from typing import Protocol

from core.document import Document


class Publisher(Protocol):
    """Contract for destinations that publish rendered documents."""

    def exists(self, title: str) -> bool:
        ...

    def count_items(self, title: str) -> int:
        ...

    def publish(self, document: Document) -> bool:
        ...
