import os
import argparse
import logging
from logging.handlers import RotatingFileHandler

from agents.jira_agent import JiraAgent
from agents.release_agent import ReleaseAgent
from agents.confluence_agent import ConfluenceAgent
from agents.planner_agent import PlannerAgent
from agents.reviewer_agent import ReviewerAgent
from agents.workflow_agent import WorkflowAgent


def main():

    print("=" * 60)
    print("JiraConf AI")
    print("=" * 60)

    jira = JiraAgent()
    release_agent = ReleaseAgent()
    confluence = ConfluenceAgent()
    planner = PlannerAgent()
    reviewer = ReviewerAgent()

    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="Run headless using first board and pending sprints")
    parser.add_argument("--board-id", type=int, help="Optional: board id to process (skip prompt)")
    parser.add_argument("--sprint-index", type=int, help="Optional: 1-based sprint index to process for the selected board")
    parser.add_argument("--sprint-name", type=str, help="Optional: sprint name to process for the selected board")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose (DEBUG) logging to console")
    parser.add_argument("--force", action="store_true", help="Force regeneration and upload even if page appears up-to-date")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = logging.getLogger("jira_conf")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Rotating file handler
    fh = RotatingFileHandler("agent.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info("Starting JiraConf AI")

    print("\nFetching Boards...\n")
    logger.debug("Fetching boards list from Jira")

    boards = jira.get_boards()

    # If auto mode or AUTO_RUN env is set, run headless on first board's pending sprints
    if args.auto or os.getenv("AUTO_RUN", "0") == "1":
        board = boards[0]
        board_id = board.id
        print(f"Auto mode: using board {board.id} - {board.name}")
        sprints = jira.get_sprints(board_id)
        pending_sprints = []
        for sprint in sprints:
            title = f"Release_Note_{sprint.name}"
            if not confluence.page_exists(title):
                pending_sprints.append(sprint)
        if not pending_sprints:
            print("No pending sprints found. Exiting.")
            return
        sprints_to_process = pending_sprints

    # If a board id is provided, skip the board prompt and optionally pick a sprint
    elif args.board_id:
        # find the board
        selected = None
        for b in boards:
            try:
                if int(b.id) == int(args.board_id):
                    selected = b
                    break
            except Exception:
                continue
        if not selected:
            print(f"Board id {args.board_id} not found. Exiting.")
            return
        board = selected
        board_id = board.id
        print(f"Using board {board.id} - {board.name}")
        sprints = jira.get_sprints(board_id)
        # choose sprint by index or name if provided
        if args.sprint_index:
            idx = args.sprint_index - 1
            if idx < 0 or idx >= len(sprints):
                print(f"Sprint index {args.sprint_index} out of range for board {board.id}")
                return
            sprints_to_process = [sprints[idx]]
        elif args.sprint_name:
            found = [s for s in sprints if s.name == args.sprint_name]
            if not found:
                print(f"Sprint named '{args.sprint_name}' not found on board {board.id}")
                return
            sprints_to_process = [found[0]]
        else:
            # default to interactive selection of a single sprint
            print(f"Sprints for board {board.id} - {board.name}")
            for i, sprint in enumerate(sprints, start=1):
                print(f"{i}. {sprint.name}")
            sprint_choice = int(input("\nSelect Sprint: "))
            sprint = sprints[sprint_choice - 1]
            sprints_to_process = [sprint]

    else:

        for board in boards:
            print(f"{board.id} - {board.name}")

        board_id = int(input("\nEnter Board ID: "))

        sprints = jira.get_sprints(board_id)

        print("\nAvailable Sprints\n")

        for i, sprint in enumerate(sprints, start=1):
            print(f"{i}. {sprint.name}")

        sprint_choice = int(input("\nSelect Sprint: "))

        sprint = sprints[sprint_choice - 1]

        sprints_to_process = [sprint]

    for sprint in sprints_to_process:

        print(f"\nFetching Done tickets from {sprint.name}...\n")
        logger.info(f"Processing sprint: {sprint.name}")

        issues = jira.get_done_work_items(sprint.name)

        print(f"Found {len(issues)} Done tickets.\n")
        logger.info(f"Found {len(issues)} done tickets for sprint {sprint.name}")

        if len(issues) == 0:
            print(f"No Done tickets found for sprint {sprint.name}.")
            continue
        title = f"Release_Note_{sprint.name}"

        page = confluence.page_exists(title)

        page_count = confluence.get_page_note_count(title) if page else 0

        if page and page_count >= len(issues) and not args.force:
            print(f"Release notes already up-to-date for {sprint.name} (page has {page_count} items). Skipping.")
            logger.info(f"Skipping sprint {sprint.name}: page has {page_count} items, issues {len(issues)}")
            continue

        if page and page_count < len(issues):
            print(f"Existing release notes found with {page_count} items; {len(issues)} done tickets found. Will update page.")

        context = {
            "issues_count": len(issues),
            "sprint": sprint.name,
            "page_exists": bool(page),
            "page_count": page_count,
            "issues": issues,
        }

        if not page:
            print(f"No Confluence page found for {sprint.name}; planner will decide the next action")

        workflow = WorkflowAgent(jira, confluence, planner, reviewer, release_agent)
        result = workflow.run(sprint, context)
        logger.info("Workflow finished for %s with stage=%s", sprint.name, result.get("stage"))

    print("All done.")


if __name__ == "__main__":
    main()