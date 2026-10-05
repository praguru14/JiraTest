from core.work_item import WorkItem
from services.jira_formatter import JiraFormatter
from sources.base import WorkItemSource


class JiraWorkItemSource(WorkItemSource):
    """Maps Jira issues into the source-neutral WorkItem model."""

    def __init__(self, jira_agent):
        self.jira_agent = jira_agent

    def fetch_done_items(self, sprint_name: str) -> list[WorkItem]:
        issues = self.jira_agent.get_done_issues(sprint_name)
        return [self.from_issue(issue) for issue in issues]

    @staticmethod
    def from_issue(issue) -> WorkItem:
        fields = issue.fields
        priority = getattr(fields, "priority", None)
        issue_type = getattr(fields, "issuetype", None)
        labels = tuple(getattr(fields, "labels", None) or ())
        title = getattr(fields, "summary", None) or ""

        return WorkItem(
            id=str(issue.key),
            title=title,
            description=JiraFormatter.get_description(issue),
            kind=getattr(issue_type, "name", None) or "Unknown",
            status=getattr(getattr(fields, "status", None), "name", None) or "",
            labels=labels,
            priority=getattr(priority, "name", None) or "None",
            metadata={"source": "jira"},
        )
