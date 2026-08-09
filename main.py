import os
import argparse
import logging
from logging.handlers import RotatingFileHandler

from agents.jira_agent import JiraAgent
from agents.release_agent import ReleaseAgent
from agents.confluence_agent import ConfluenceAgent
from agents.planner_agent import PlannerAgent
from agents.reviewer_agent import ReviewerAgent

from services.html_builder import HTMLBuilder


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

        issues = jira.get_done_issues(sprint.name)

        print(f"Found {len(issues)} Done tickets.\n")
        logger.info(f"Found {len(issues)} done tickets for sprint {sprint.name}")

        if len(issues) == 0:
            print("No Done tickets found for sprint {sprint.name}.")
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
            "stage": "start",
            "issues_count": len(issues),
            "sprint": sprint.name,
            "page_exists": bool(page),
            "page_count": page_count
        }

        # If page exists but is missing tickets, or page is missing, force generation
        initial_action = None
        if page and page_count < len(issues):
            initial_action = "GENERATE_RELEASE_NOTES"
        # If no page exists at all, we should generate release notes
        if not page:
            print(f"No Confluence page found for {sprint.name}; forcing generation")
            logger.info(f"No Confluence page found for {sprint.name}; will generate")
            initial_action = "GENERATE_RELEASE_NOTES"

        fallback = [
            "GENERATE_RELEASE_NOTES",
            "REVIEW_RELEASE_NOTES",
            "UPLOAD_CONFLUENCE",
            "FINISH"
        ]

        fallback_idx = 0

        release_notes = []

        while True:

            # if we have an enforced initial action, use it first
            if initial_action:
                action = initial_action
                logger.debug(f"Forcing initial action: {action}")
                initial_action = None
            else:
                try:
                    decision = planner.next_action(context)
                    action = decision.get("action") if isinstance(decision, dict) else None
                except Exception:
                    action = None

                # If planner asks to generate but we've already progressed past generation,
                # map to the appropriate next step to avoid repeated generate loops.
                if action == "GENERATE_RELEASE_NOTES" and context.get("stage") in ("generated", "reviewed", "uploaded"):
                    stage = context.get("stage")
                    logger.debug(f"Planner requested GENERATE but stage is '{stage}'; remapping action")
                    if stage == "generated":
                        action = "REVIEW_RELEASE_NOTES"
                    elif stage == "reviewed":
                        action = "UPLOAD_CONFLUENCE"
                    else:
                        action = "FINISH"

                if action is None:
                    action = fallback[fallback_idx]
            print(f"Planner decided: {action}")

            if action == "GENERATE_RELEASE_NOTES":

                logger.info("Action=GENERATE_RELEASE_NOTES")
                print("Generating Release Notes...\n")

                release_notes = release_agent.generate_release_notes(issues)

                context["release_notes_count"] = len(release_notes)
                # mark that generation completed so planner has context
                context["stage"] = "generated"
                # force the next loop iteration to review the generated notes
                initial_action = "REVIEW_RELEASE_NOTES"

            elif action == "REVIEW_RELEASE_NOTES":

                logger.info("Action=REVIEW_RELEASE_NOTES")
                print("Reviewing Release Notes...\n")

                review = reviewer.review(release_notes)

                print("Review result:")
                print(review)
                logger.debug(f"Reviewer output: {review}")
                # If reviewer returns a dict with validation, advance to upload
                if isinstance(review, dict) and review.get("valid"):
                    context["stage"] = "reviewed"
                    logger.info("Review passed validation; scheduling upload")
                    # force the next loop iteration to upload
                    initial_action = "UPLOAD_CONFLUENCE"
                else:
                    # allow a limited number of regeneration attempts
                    attempts = context.get("regen_attempts", 0) + 1
                    context["regen_attempts"] = attempts
                    if attempts <= 2:
                        print(f"Review failed or invalid; regenerating (attempt {attempts})")
                        # force generation next
                        initial_action = "GENERATE_RELEASE_NOTES"
                    else:
                        print("Review failed after retries; finishing to avoid loop.")
                        initial_action = "FINISH"

            elif action == "UPLOAD_CONFLUENCE":

                logger.info("Action=UPLOAD_CONFLUENCE")
                print("Uploading to Confluence...\n")

                html = HTMLBuilder.build(sprint.name, release_notes)

                page_title = f"Release_Note_{sprint.name}"
                logger.debug(f"Uploading page title={page_title}, html length={len(html)}")
                confluence.create_or_update_page(page_title, html)

                context["stage"] = "uploaded"
                logger.info(f"Uploaded Confluence page for sprint {sprint.name}")
                # finish next
                initial_action = "FINISH"

            elif action == "FINISH":

                print("\nDone!")

                break

            # advance fallback pointer (so if planner fails we'll progress)
            if fallback_idx < len(fallback) - 1:
                fallback_idx += 1

    print("All done.")


if __name__ == "__main__":
    main()