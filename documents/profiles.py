from core.document_profile import DocumentProfile
from core.work_item import WorkItem


def release_description(item: WorkItem) -> str:
    return item.title or item.description or f"Updates related to {item.id}."


RELEASE_NOTES = DocumentProfile(
    name="release_notes",
    prompt_file="release_prompt.txt",
    review_prompt_file="reviewer_prompt.txt",
    required_fields=("label", "ticket_number", "description"),
    fallback_description=release_description,
)
