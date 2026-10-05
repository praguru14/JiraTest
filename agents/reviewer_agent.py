from agents.content_reviewer import ContentReviewer
from documents.profiles import RELEASE_NOTES


class ReviewerAgent(ContentReviewer):
    """Compatibility wrapper for the release-notes document profile."""

    def __init__(self):
        super().__init__(RELEASE_NOTES)
