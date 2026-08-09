import time
import argparse
import logging
from datetime import datetime

from agents.jira_agent import JiraAgent
from agents.release_agent import ReleaseAgent
from agents.confluence_agent import ConfluenceAgent
from agents.planner_agent import PlannerAgent
from agents.reviewer_agent import ReviewerAgent
from services.html_builder import HTMLBuilder


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
        # Ask planner first to decide the flow
        plan_context = {"stage": "plan", "sprint": sprint.name}
        decision = planner.next_action(plan_context)
        action = decision.get("action") if isinstance(decision, dict) else None

        logger.info(f"Planner decision for {sprint.name}: {action}")

        # Gather data only as needed
        issues = []
        page = False
        page_count = 0

        if action in ("GENERATE_RELEASE_NOTES", "REVIEW_RELEASE_NOTES", "UPLOAD_CONFLUENCE", None):
            issues = jira.get_done_issues(sprint.name)
            logger.info(f"Found {len(issues)} done tickets for sprint {sprint.name}")

        if action in ("UPLOAD_CONFLUENCE", "REVIEW_RELEASE_NOTES", "GENERATE_RELEASE_NOTES", None):
            page = confluence.page_exists(title)
            page_count = confluence.get_page_note_count(title) if page else 0

        # If page is already up-to-date and planner didn't ask for force, skip
        if page and issues and page_count >= len(issues) and action != "FORCE_UPDATE":
            logger.info(f"Skipping {sprint.name}: page up-to-date ({page_count} items)")
            return

        release_notes = []

        if action in ("GENERATE_RELEASE_NOTES", None, "FORCE_UPDATE"):
            release_notes = release_agent.generate_release_notes(issues)
            logger.info(f"Generated {len(release_notes)} notes for {sprint.name}")

        # Review before publishinga
        if release_notes:
            try:
                review = reviewer.review(release_notes)
                logger.info(f"Review result for {sprint.name}: {review}")
                approved = review.get("approved", True) if isinstance(review, dict) else True
            except Exception as e:
                logger.exception(f"Review failed for {sprint.name}: {e}")
                approved = False

            if approved:
                html = HTMLBuilder.build(sprint.name, release_notes)
                confluence.create_or_update_page(sprint.name, html)
                logger.info(f"Uploaded release notes for {sprint.name}")
            else:
                logger.info(f"Release notes for {sprint.name} not approved; skipping upload")

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
