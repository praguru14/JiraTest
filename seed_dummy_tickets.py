import argparse
import logging

import config
from agents.jira_agent import JiraAgent


logger = logging.getLogger("jira_conf.seed")
LABEL = "jira-conf-dummy"


def _escape_jql(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _existing_dummy_tickets(jira, summary_prefix):
    prefix = _escape_jql(summary_prefix)
    jql = (
        f'project = "{config.JIRA_PROJECT_KEY}" '
        f'AND labels = "{LABEL}" AND summary ~ "{prefix}"'
    )
    return jira.search_issues(jql, maxResults=100)


def _move_to_done(jira, issue):
    transitions = jira.transitions(issue)
    done_transition = next(
        (
            transition
            for transition in transitions
            if transition["name"].strip().lower() == "done"
        ),
        None,
    )
    if not done_transition:
        logger.warning("No Done transition is available for %s", issue.key)
        return False

    jira.transition_issue(issue, done_transition["id"])
    return True


def seed_tickets(count, summary_prefix, sprint_id=None, dry_run=False):
    jira = JiraAgent().jira
    existing = _existing_dummy_tickets(jira, summary_prefix)
    existing_summaries = {issue.fields.summary for issue in existing}
    created = []

    for index in range(1, count + 1):
        summary = f"{summary_prefix} {index}"
        if summary in existing_summaries:
            print(f"Skipping existing ticket: {summary}")
            continue

        fields = {
            "project": {"key": config.JIRA_PROJECT_KEY},
            "summary": summary,
            "description": (
                "Demo ticket created by JiraConf. "
                "This ticket is safe to remove after the demonstration."
            ),
            "issuetype": {"name": "Task"},
            "labels": [LABEL],
        }

        if dry_run:
            print(f"Would create: {summary}")
            continue

        issue = jira.create_issue(fields=fields)
        created.append(issue)
        print(f"Created {issue.key}: {summary}")

        if _move_to_done(jira, issue):
            print(f"Moved {issue.key} to Done")

    if sprint_id and created and not dry_run:
        jira.add_issues_to_sprint(sprint_id, [issue.key for issue in created])
        print(f"Added {len(created)} ticket(s) to sprint {sprint_id}")

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Create demo Jira tickets for JiraConf testing."
    )
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument(
        "--prefix",
        default="JiraConf Demo",
        help="Summary prefix used to identify seeded tickets",
    )
    parser.add_argument(
        "--sprint-id",
        type=int,
        help="Optional Jira sprint ID to assign created tickets to",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview tickets without creating anything",
    )
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be at least 1")

    seed_tickets(
        count=args.count,
        summary_prefix=args.prefix,
        sprint_id=args.sprint_id,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()