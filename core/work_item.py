from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkItem:
    """Source-neutral representation of a unit of work."""

    id: str
    title: str
    description: str = ""
    kind: str = "Unknown"
    status: str = ""
    labels: tuple[str, ...] = ()
    priority: str = "None"
    metadata: dict[str, Any] = field(default_factory=dict)
