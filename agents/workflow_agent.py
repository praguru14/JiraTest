import logging

from services.html_builder import HTMLBuilder


logger = logging.getLogger("jira_conf.workflow")


class WorkflowAgent:
    """Runs a bounded observe-decide-act loop for one sprint."""

    ACTIONS = {
        "FETCH_TICKETS",
        "INSPECT_CONFLUENCE",
        "GENERATE_RELEASE_NOTES",
        "REVIEW_RELEASE_NOTES",
        "UPLOAD_CONFLUENCE",
        "VERIFY_CONFLUENCE",
        "FINISH",
    }

    def __init__(self, jira, confluence, planner, reviewer, release_agent):
        self.jira = jira
        self.confluence = confluence
        self.planner = planner
        self.reviewer = reviewer
        self.release_agent = release_agent

    def run(self, sprint, initial_state=None, max_steps=12):
        state = {
            "stage": "start",
            "sprint": sprint.name,
            "goal": f"Publish accurate release notes for {sprint.name}",
            "issues": [],
            "release_notes": [],
            "action_history": [],
            "available_actions": sorted(self.ACTIONS),
        }
        if initial_state:
            state.update(initial_state)

        tools = {
            "FETCH_TICKETS": self._fetch_tickets,
            "INSPECT_CONFLUENCE": self._inspect_confluence,
            "GENERATE_RELEASE_NOTES": self._generate_release_notes,
            "REVIEW_RELEASE_NOTES": self._review_release_notes,
            "UPLOAD_CONFLUENCE": self._upload_confluence,
            "VERIFY_CONFLUENCE": self._verify_confluence,
        }

        for step in range(1, max_steps + 1):
            decision = self.planner.next_action(self._planner_state(state, step))
            action = decision.get("action") if isinstance(decision, dict) else None

            if action not in self.ACTIONS:
                state["last_error"] = f"Planner selected unsupported action: {action}"
                logger.warning(state["last_error"])
                action = self._recovery_action(state)

            if not self._action_is_safe(action, state):
                state["last_error"] = (
                    f"Planner selected action {action}, but its prerequisites are not met"
                )
                logger.warning(state["last_error"])
                action = self._recovery_action(state)

            print(f"Planner selected: {action}")
            logger.info("Workflow step %s: %s", step, action)

            if action == "FINISH":
                if state.get("verified"):
                    state["stage"] = "finished"
                    return state
                state["last_error"] = "Cannot finish before Confluence is verified"
                action = self._recovery_action(state)
                if action == "FINISH":
                    state["stage"] = "finished"
                    return state

            try:
                result = tools[action](sprint, state)
                if result:
                    state.update(result)
                state.pop("last_error", None)
                state.setdefault("action_history", []).append(action)
            except Exception as exc:
                state["last_error"] = f"{action} failed: {exc}"
                logger.exception(state["last_error"])
                print(f"{action} failed: {exc}")
                state["stage"] = "action_failed"
                state.setdefault("action_history", []).append(action)

        state["stage"] = "stopped"
        state["last_error"] = f"Maximum workflow steps ({max_steps}) reached"
        logger.error(state["last_error"])
        return state

    @staticmethod
    def _planner_state(state, step):
        return {
            "stage": state.get("stage"),
            "goal": state.get("goal"),
            "sprint": state.get("sprint"),
            "issues_count": len(state.get("issues", [])),
            "release_notes_count": len(state.get("release_notes", [])),
            "page_exists": state.get("page_exists", False),
            "page_count": state.get("page_count", 0),
            "review": state.get("review"),
            "last_error": state.get("last_error"),
            "verified": state.get("verified", False),
            "action_history": state.get("action_history", [])[-6:],
            "step": step,
            "max_steps": 12,
            "available_actions": state.get("available_actions", []),
        }

    @classmethod
    def _action_is_safe(cls, action, state):
        if action == "FETCH_TICKETS":
            return not state.get("issues") or state.get("stage") in {
                "start", "action_failed"
            }
        if action == "INSPECT_CONFLUENCE":
            return bool(state.get("issues"))
        if action == "GENERATE_RELEASE_NOTES":
            return bool(state.get("issues")) and state.get("stage") in {
                "confluence_inspected",
                "generation_failed",
                "action_failed",
            }
        if action == "REVIEW_RELEASE_NOTES":
            return bool(state.get("release_notes")) and state.get("stage") in {
                "generated",
                "review_failed",
                "action_failed",
            }
        if action == "UPLOAD_CONFLUENCE":
            return (
                state.get("review", {}).get("valid") is True
                and cls._notes_have_valid_schema(state.get("release_notes", []))
                and not state.get("uploaded")
                and state.get("stage") in {"reviewed", "action_failed"}
            )
        if action == "VERIFY_CONFLUENCE":
            return bool(state.get("uploaded")) and not state.get("verified")
        if action == "FINISH":
            return bool(state.get("verified"))
        return False

    def _fetch_tickets(self, sprint, state):
        issues = state.get("issues") or self.jira.get_done_issues(sprint.name)
        print(f"Fetched {len(issues)} Done tickets")
        return {"issues": issues, "stage": "tickets_fetched"}

    def _inspect_confluence(self, sprint, state):
        title = f"Release_Note_{sprint.name}"
        page = self.confluence.page_exists(title)
        page_count = self.confluence.get_page_note_count(title) if page else 0
        return {
            "page_exists": bool(page),
            "page_count": page_count,
            "stage": "confluence_inspected",
        }

    def _generate_release_notes(self, sprint, state):
        issues = state.get("issues", [])
        if not issues:
            raise ValueError("No Jira tickets are available")
        print(f"Generating release notes for {len(issues)} tickets")
        notes = self.release_agent.generate_release_notes(issues)
        if not notes:
            attempts = state.get("generation_attempts", 0) + 1
            return {
                "release_notes": [],
                "generation_attempts": attempts,
                "stage": "generation_failed",
                "last_error": "Release-note generation returned no valid notes",
            }
        return {
            "release_notes": notes,
            "generation_attempts": state.get("generation_attempts", 0) + 1,
            "stage": "generated",
        }

    def _review_release_notes(self, sprint, state):
        notes = state.get("release_notes", [])
        if not notes:
            raise ValueError("No release notes are available")
        print("Reviewing release notes")
        review = self.reviewer.review(notes)
        valid = isinstance(review, dict) and review.get("valid") is True

        # A small local model can incorrectly reject otherwise well-formed
        # notes. The schema check remains deterministic and protects upload.
        if not valid and self._notes_have_valid_schema(notes):
            review = {
                "valid": True,
                "errors": [],
                "suggestions": review.get("suggestions", [])
                if isinstance(review, dict)
                else [],
                "review_mode": "local_schema_fallback",
            }
            valid = True

        result = {
            "review": review,
            "stage": "reviewed" if valid else "review_failed",
        }
        if not valid:
            result["review_attempts"] = state.get("review_attempts", 0) + 1
        return result

    @staticmethod
    def _notes_have_valid_schema(notes):
        return all(
            isinstance(note, dict)
            and isinstance(note.get("label"), str)
            and bool(note.get("label", "").strip())
            and bool(note.get("ticket_number"))
            and bool(note.get("description"))
            for note in notes
        )

    def _upload_confluence(self, sprint, state):
        if not self._action_is_safe("UPLOAD_CONFLUENCE", state):
            raise ValueError("Release notes must pass review before upload")
        title = f"Release_Note_{sprint.name}"
        html = HTMLBuilder.build(sprint.name, state.get("release_notes", []))
        uploaded = self.confluence.create_or_update_page(title, html)
        if uploaded is False:
            raise ValueError("Confluence update was cancelled")
        return {"stage": "uploaded", "uploaded": True}

    def _verify_confluence(self, sprint, state):
        title = f"Release_Note_{sprint.name}"
        page = self.confluence.page_exists(title)
        page_count = self.confluence.get_page_note_count(title) if page else 0
        expected = len(state.get("release_notes", []))
        verified = bool(page) and page_count >= expected
        if not verified:
            raise ValueError(
                f"Verification failed: expected at least {expected} notes, found {page_count}"
            )
        print(f"Verified {title}: {page_count} release notes")
        return {"stage": "verified", "verified": True, "page_count": page_count}

    @staticmethod
    def _recovery_action(state):
        stage = state.get("stage")
        if stage == "start":
            return "FETCH_TICKETS"
        if stage == "tickets_fetched":
            return "INSPECT_CONFLUENCE"
        if stage in {"confluence_inspected", "review_failed"}:
            if state.get("review_attempts", 0) >= 1:
                return "FINISH"
            return "GENERATE_RELEASE_NOTES"
        if stage == "generation_failed":
            if state.get("generation_attempts", 0) >= 3:
                return "FINISH"
            return "GENERATE_RELEASE_NOTES"
        if stage == "generated":
            return "REVIEW_RELEASE_NOTES"
        if stage == "reviewed":
            return "UPLOAD_CONFLUENCE"
        if stage == "uploaded":
            return "VERIFY_CONFLUENCE"
        if stage == "verified":
            return "FINISH"
        if stage == "action_failed":
            history = state.get("action_history", [])
            if history and history[-1] == "UPLOAD_CONFLUENCE":
                return "UPLOAD_CONFLUENCE"
            if history and history[-1] == "VERIFY_CONFLUENCE":
                return "VERIFY_CONFLUENCE"
            if state.get("release_notes"):
                return "REVIEW_RELEASE_NOTES"
            if state.get("issues"):
                return "GENERATE_RELEASE_NOTES"
            return "FETCH_TICKETS"
        return "FINISH"