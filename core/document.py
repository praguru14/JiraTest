from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    """Rendered output that can be sent to a publisher."""

    title: str
    body: str
    format: str = "html"
    metadata: dict[str, Any] = field(default_factory=dict)
