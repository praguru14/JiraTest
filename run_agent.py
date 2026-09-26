import time
import argparse
import logging
from datetime import datetime

from agents.jira_agent import JiraAgent
from agents.release_agent import ReleaseAgent
from agents.confluence_agent import ConfluenceAgent
from agents.planner_agent import PlannerAgent
from agents.reviewer_agent import ReviewerAgent
from agents.workflow_agent import WorkflowAgent


logger = logging.getLogger("jira_conf_agent")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("agent.log")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)
# also log to console for immediate feedback
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)


def process_sprint(jira, confluence, planner, reviewer, release_agent, sprint, board):
    title = f"Release_Note_{sprint.name}"

    try:
        issues = jira.get_done_issues(sprint.name)
        page = confluence.page_exists(title)
        page_count = confluence.get_page_note_count(title) if page else 0

        if page and issues and page_count >= len(issues):
            logger.info(f"Skipping {sprint.name}: page up-to-date ({page_count} items)")
            return

        workflow = WorkflowAgent(jira, confluence, planner, reviewer, release_agent)
        result = workflow.run(
            sprint,
            {
                "issues": issues,
                "page_exists": bool(page),
                "page_count": page_count,
            },
        )
        logger.info("Workflow finished for %s with stage=%s", sprint.name, result.get("stage"))

    except Exception as e:
        logger.exception(f"Error processing sprint {sprint.name}: {e}")


def run_loop(interval_minutes: int, once: bool = False, board_id: int | None = None):

    jira = JiraAgent()
    release_agent = ReleaseAgent()
    confluence = ConfluenceAgent()
    planner = PlannerAgent()
    reviewer = ReviewerAgent()

    while True:
        try:
            logger.info("Agent run starting")

            boards = jira.get_boards()

            for board in boards:
                if board_id and int(board.id) != int(board_id):
                    continue

                sprints = jira.get_sprints(board.id)

                for sprint in sprints:
                    title = f"Release_Note_{sprint.name}"
                    page = confluence.page_exists(title)
                    page_count = confluence.get_page_note_count(title) if page else 0

                    issues = jira.get_done_issues(sprint.name)

                    if not issues:
                        continue

                    logger.info(f"Processing sprint {sprint.name}: page={page} page_count={page_count} issues={len(issues)}")

                    if page and page_count >= len(issues):
                        logger.info(f"{sprint.name} up-to-date: page {page_count} vs issues {len(issues)}")
                        continue

                    process_sprint(jira, confluence, planner, reviewer, release_agent, sprint, board)

            logger.info("Agent run finished")

            if once:
                break

            time.sleep(max(10, interval_minutes * 60))

        except KeyboardInterrupt:
            logger.info("Agent interrupted by user")
            break
        except Exception:
            logger.exception("Unexpected error in agent loop; sleeping before retrying")
            time.sleep(60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=10, help="Polling interval in minutes")
    parser.add_argument("--board-id", type=int, help="Optional: process only this board id")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose (DEBUG) logging to console and file")

    args = parser.parse_args()
    # If verbose, increase logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for h in logger.handlers:
            h.setLevel(logging.DEBUG)

    logger.info(f"Starting agent (once={args.once}, interval={args.interval}m, board_id={args.board_id}, verbose={args.verbose})")
    run_loop(args.interval, once=args.once, board_id=args.board_id)


if __name__ == "__main__":
    main()
