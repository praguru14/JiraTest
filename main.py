from agents.jira_agent import JiraAgent
from agents.release_agent import ReleaseAgent
from agents.confluence_agent import ConfluenceAgent

from services.html_builder import HTMLBuilder


def main():

    print("=" * 60)
    print("JiraConf AI")
    print("=" * 60)

    jira = JiraAgent()
    release_agent = ReleaseAgent()
    confluence = ConfluenceAgent()

    print("\nFetching Boards...\n")

    boards = jira.get_boards()

    for board in boards:
        print(f"{board.id} - {board.name}")

    board_id = int(input("\nEnter Board ID: "))

    sprints = jira.get_sprints(board_id)

    print("\nAvailable Sprints\n")

    for i, sprint in enumerate(sprints, start=1):
        print(f"{i}. {sprint.name}")

    sprint_choice = int(input("\nSelect Sprint: "))

    sprint = sprints[sprint_choice - 1]

    print(f"\nFetching Done tickets from {sprint.name}...\n")

    issues = jira.get_done_issues(sprint.name)

    print(f"Found {len(issues)} Done tickets.\n")

    if len(issues) == 0:
        print("No Done tickets found.")
        return

    print("Generating Release Notes...\n")

    release_notes = release_agent.generate_release_notes(
        issues
    )

    html = HTMLBuilder.build(
        sprint.name,
        release_notes
    )

    print("Uploading to Confluence...\n")

    confluence.create_or_update_page(
        sprint.name,
        html
    )

    print("\nDone!")


if __name__ == "__main__":
    main()