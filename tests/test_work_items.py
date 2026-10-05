import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

import config

from agents.release_agent import ReleaseAgent
from agents.workflow_agent import WorkflowAgent
from core.document import Document
from documents.profiles import RELEASE_NOTES
from core.work_item import WorkItem
from publishers.confluence_publisher import ConfluencePublisher
from publishers.file_publisher import FilePublisher
from services.html_builder import HTMLBuilder
from sources.jira_source import JiraWorkItemSource
from sources.csv_source import CsvWorkItemSource


class JiraWorkItemSourceTests(unittest.TestCase):
    def test_csv_source_maps_and_filters_rows(self):
        csv_text = (
            "id,title,description,type,status,labels,priority\n"
            'CSV-1,CSV feature,Useful update,Feature,Done,"public,ignored",High\n'
            "CSV-2,Pending work,Not ready,Task,In Progress,,Low\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as stream:
            stream.write(csv_text)
            path = stream.name

        try:
            items = CsvWorkItemSource(path).fetch_done_items()
        finally:
            Path(path).unlink(missing_ok=True)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "CSV-1")
        self.assertEqual(items[0].labels, ("public", "ignored"))

    def test_maps_jira_issue_to_source_neutral_work_item(self):
        issue = SimpleNamespace(
            key="PG2-24",
            fields=SimpleNamespace(
                summary="Export report",
                description="Lets customers export a report.",
                labels=["customer-facing"],
                priority=SimpleNamespace(name="High"),
                issuetype=SimpleNamespace(name="Story"),
                status=SimpleNamespace(name="Done"),
            ),
        )

        item = JiraWorkItemSource.from_issue(issue)

        self.assertEqual(item.id, "PG2-24")
        self.assertEqual(item.title, "Export report")
        self.assertEqual(item.kind, "Story")
        self.assertEqual(item.labels, ("customer-facing",))
        self.assertEqual(item.priority, "High")

    def test_release_agent_preserves_normalized_items(self):
        item = WorkItem(id="PG2-25", title="Search improvements")

        self.assertIs(ReleaseAgent._coerce_work_item(item), item)


class DocumentPublisherTests(unittest.TestCase):
    def test_workflow_accepts_a_custom_source(self):
        class FakeSource:
            def fetch_done_items(self, scope):
                return [WorkItem(id=f"{scope}-1", title="Custom item")]

        workflow = WorkflowAgent(
            jira=None,
            confluence=None,
            planner=None,
            reviewer=None,
            release_agent=None,
            source=FakeSource(),
        )

        result = workflow._fetch_items("Custom scope", {})

        self.assertEqual(result["issues"][0].id, "Custom scope-1")
        self.assertTrue(
            workflow._action_is_safe(
                "PUBLISH_DOCUMENT",
                {
                    "review": {"valid": True},
                    "release_notes": [
                        {
                            "label": "Feature",
                            "ticket_number": "X-1",
                            "description": "Done",
                        }
                    ],
                    "stage": "reviewed",
                    "uploaded": False,
                },
            )
        )

    def test_release_profile_defines_generation_and_review(self):
        self.assertEqual(RELEASE_NOTES.name, "release_notes")
        self.assertEqual(RELEASE_NOTES.prompt_file, "release_prompt.txt")
        self.assertEqual(RELEASE_NOTES.review_prompt_file, "reviewer_prompt.txt")
        self.assertEqual(RELEASE_NOTES.required_fields, ("label", "ticket_number", "description"))

    def test_html_builder_returns_a_document(self):
        original_jira_url = config.JIRA_URL
        config.JIRA_URL = "https://example.atlassian.net"
        try:
            document = HTMLBuilder.build_document(
                "Sprint 1",
                [{"label": "Feature", "ticket_number": "X-1", "description": "Done"}],
            )
        finally:
            config.JIRA_URL = original_jira_url

        self.assertIsInstance(document, Document)
        self.assertEqual(document.title, "Release_Note_Sprint 1")
        self.assertEqual(document.format, "html")
        self.assertIn("X-1", document.body)
        self.assertIn('href="https://example.atlassian.net/browse/X-1"', document.body)

    def test_confluence_publisher_delegates_document_body(self):
        class FakeConfluence:
            def page_exists(self, title):
                return title == "Existing"

            def get_page_note_count(self, title):
                return 2

            def create_or_update_page(self, title, body):
                self.published = (title, body)
                return True

        confluence = FakeConfluence()
        publisher = ConfluencePublisher(confluence)
        document = Document(title="Existing", body="<p>content</p>")

        self.assertTrue(publisher.exists("Existing"))
        self.assertEqual(publisher.count_items("Existing"), 2)
        self.assertTrue(publisher.publish(document))
        self.assertEqual(confluence.published, ("Existing", "<p>content</p>"))

    def test_file_publisher_writes_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "output.html"
            document = Document(title="Test", body="<table><tr></tr><tr></tr></table>")

            publisher = FilePublisher(path)

            self.assertTrue(publisher.publish(document))
            self.assertTrue(publisher.exists("Test"))
            self.assertEqual(publisher.count_items("Test"), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), document.body)


if __name__ == "__main__":
    unittest.main()
