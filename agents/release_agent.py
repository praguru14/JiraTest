from agents.content_generator import ContentGenerator
from documents.profiles import RELEASE_NOTES


class ReleaseAgent(ContentGenerator):
    """Compatibility wrapper for the release-notes document profile."""

    def __init__(self):
        super().__init__(RELEASE_NOTES)

    def generate_release_notes(self, issues):
        return self.generate(issues)
