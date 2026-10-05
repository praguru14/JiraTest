from core.document import Document
from publishers.base import Publisher


class ConfluencePublisher(Publisher):
    """Publishes generic Documents through the existing Confluence agent."""

    def __init__(self, confluence_agent):
        self.confluence = confluence_agent

    def exists(self, title: str) -> bool:
        return bool(self.confluence.page_exists(title))

    def count_items(self, title: str) -> int:
        return self.confluence.get_page_note_count(title)

    def get_url(self, title: str):
        return self.confluence.get_page_url(title)

    def publish(self, document: Document) -> bool:
        return self.confluence.create_or_update_page(document.title, document.body)
