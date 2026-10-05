from dataclasses import dataclass
from typing import Callable

from core.work_item import WorkItem


@dataclass(frozen=True)
class DocumentProfile:
    """Configuration for generating one structured document item."""

    name: str
    prompt_file: str
    review_prompt_file: str
    required_fields: tuple[str, ...]
    fallback_description: Callable[[WorkItem], str]
