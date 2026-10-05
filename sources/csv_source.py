import csv
from pathlib import Path

from core.work_item import WorkItem


class CsvWorkItemSource:
    """Loads normalized work items from a CSV export."""

    def __init__(self, path):
        self.path = Path(path)

    def fetch_done_items(self, scope: str = "Done") -> list[WorkItem]:
        with self.path.open(newline="", encoding="utf-8-sig") as stream:
            rows = csv.DictReader(stream)
            items = [self.from_row(row) for row in rows]

        if not scope:
            return items
        return [item for item in items if item.status.lower() == scope.lower()]

    @staticmethod
    def from_row(row: dict[str, str]) -> WorkItem:
        labels = tuple(
            label.strip()
            for label in (row.get("labels") or "").split(",")
            if label.strip()
        )
        return WorkItem(
            id=(row.get("id") or row.get("key") or "").strip(),
            title=(row.get("title") or row.get("summary") or "").strip(),
            description=(row.get("description") or "").strip(),
            kind=(row.get("kind") or row.get("type") or "Unknown").strip(),
            status=(row.get("status") or "").strip(),
            labels=labels,
            priority=(row.get("priority") or "None").strip(),
            metadata={"source": "csv"},
        )
