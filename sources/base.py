from typing import Protocol

from core.work_item import WorkItem


class WorkItemSource(Protocol):
    """Contract for adapters that provide normalized work items."""

    def fetch_done_items(self, scope: str) -> list[WorkItem]:
        ...
