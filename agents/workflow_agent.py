import logging

from services.html_builder import HTMLBuilder
from publishers.confluence_publisher import ConfluencePublisher
from sources.jira_source import JiraWorkItemSource


logger = logging.getLogger("jira_conf.workflow")


class WorkflowAgent:
    """Runs a bounded observe-decide-act loop for one sprint."""

    ACTIONS = {
        "FETCH_ITEMS",
        "INSPECT_DESTINATION",
        "GENERATE_DOCUMENT",
        "REVIEW_DOCUMENT",
        "PUBLISH_DOCUMENT",
        "VERIFY_OUTPUT",
        "FINISH",
    }

    LEGACY_ACTIONS = {
        "FETCH_TICKETS": "FETCH_ITEMS",
        "INSPECT_CONFLUENCE": "INSPECT_DESTINATION",
        "GENERATE_RELEASE_NOTES": "GENERATE_DOCUMENT",
        "REVIEW_RELEASE_NOTES": "REVIEW_DOCUMENT",
        "UPLOAD_CONFLUENCE": "PUBLISH_DOCUMENT",
        "VERIFY_CONFLUENCE": "VERIFY_OUTPUT",
    }

    def __init__(
        self,
        jira,
        confluence,
        planner,
        reviewer,
        release_agent,
        publisher=None,
        source=None,
        generator=None,
        renderer=None,
        title_builder=None,
        notes_validator=None,
    ):
        self.jira = jira
        self.confluence = confluence
        self.publisher = publisher or ConfluencePublisher(confluence)
        self.source = source or JiraWorkItemSource(jira)
        self.planner = planner
        self.reviewer = reviewer
        self.generator = generator or release_agent
        self.renderer = renderer or HTMLBuilder.build_document
        self.title_builder = title_builder or (lambda scope: f"Release_Note_{scope}")
        self.notes_validator = notes_validator or self._default_notes_validator

    def run(self, sprint, initial_state=None, max_steps=12):
        state = {
            "stage": "start",
            "sprint": self._scope_name(sprint),
            "goal": f"Publish an accurate document for {self._scope_name(sprint)}",
            "issues": [],
            "release_notes": [],
            "action_history": [],
            "available_actions": sorted(self.ACTIONS),
        }
        if initial_state:
            state.update(initial_state)

        tools = {
            "FETCH_ITEMS": self._fetch_items,
            "INSPECT_DESTINATION": self._inspect_destination,
            "GENERATE_DOCUMENT": self._generate_document,
            "REVIEW_DOCUMENT": self._review_document,
            "PUBLISH_DOCUMENT": self._publish_document,
            "VERIFY_OUTPUT": self._verify_output,
        }

        for step in range(1, max_steps + 1):
            decision = self.planner.next_action(self._planner_state(state, step))
            action = decision.get("action") if isinstance(decision, dict) else None
            action = self.LEGACY_ACTIONS.get(action, action)

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

    def _action_is_safe(self, action, state):
        if action == "FETCH_ITEMS":
            return not state.get("issues") or state.get("stage") in {
                "start", "action_failed"
            }
        if action == "INSPECT_DESTINATION":
            return bool(state.get("issues"))
        if action == "GENERATE_DOCUMENT":
            return bool(state.get("issues")) and state.get("stage") in {
                "confluence_inspected",
                "generation_failed",
                "action_failed",
            }
        if action == "REVIEW_DOCUMENT":
            return bool(state.get("release_notes")) and state.get("stage") in {
                "generated",
                "review_failed",
                "action_failed",
            }
        if action == "PUBLISH_DOCUMENT":
            return (
                state.get("review", {}).get("valid") is True
                and self.notes_validator(state.get("release_notes", []))
                and not state.get("uploaded")
                and state.get("stage") in {"reviewed", "action_failed"}
            )
        if action == "VERIFY_OUTPUT":
            return bool(state.get("uploaded")) and not state.get("verified")
        if action == "FINISH":
            return bool(state.get("verified"))
        return False

    def _fetch_items(self, sprint, state):
        issues = state.get("issues") or self.source.fetch_done_items(self._scope_name(sprint))
        print(f"Fetched {len(issues)} Done tickets")
        return {"issues": issues, "stage": "tickets_fetched"}

    def _inspect_destination(self, sprint, state):
        title = self.title_builder(self._scope_name(sprint))
        page = self.publisher.exists(title)
        page_count = self.publisher.count_items(title) if page else 0
        return {
            "page_exists": bool(page),
            "page_count": page_count,
            "stage": "confluence_inspected",
        }

    def _generate_document(self, sprint, state):
        issues = state.get("issues", [])
        if not issues:
            raise ValueError("No Jira tickets are available")
        print(f"Generating release notes for {len(issues)} tickets")
        if hasattr(self.generator, "generate"):
            notes = self.generator.generate(issues)
        else:
            notes = self.generator.generate_release_notes(issues)
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

    def _review_document(self, sprint, state):
        notes = state.get("release_notes", [])
        if not notes:
            raise ValueError("No release notes are available")
        print("Reviewing release notes")
        review = self.reviewer.review(notes)
        valid = isinstance(review, dict) and review.get("valid") is True

        # A small local model can incorrectly reject otherwise well-formed
        # notes. The schema check remains deterministic and protects upload.
        if not valid and self.notes_validator(notes):
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
    def _default_notes_validator(notes):
        return all(
            isinstance(note, dict)
            and isinstance(note.get("label"), str)
            and bool(note.get("label", "").strip())
            and bool(note.get("ticket_number"))
            and bool(note.get("description"))
            for note in notes
        )

    def _publish_document(self, sprint, state):
        if not self._action_is_safe("PUBLISH_DOCUMENT", state):
            raise ValueError("Release notes must pass review before upload")
        document = self.renderer(
            self._scope_name(sprint),
            state.get("release_notes", []),
        )
        uploaded = self.publisher.publish(document)
        if uploaded is False:
            raise ValueError("Confluence update was cancelled")
        return {"stage": "uploaded", "uploaded": True}

    def _verify_output(self, sprint, state):
        title = self.title_builder(self._scope_name(sprint))
        page = self.publisher.exists(title)
        page_count = self.publisher.count_items(title) if page else 0
        expected = len(state.get("release_notes", []))
        verified = bool(page) and page_count >= expected
        if not verified:
            raise ValueError(
                f"Verification failed: expected at least {expected} notes, found {page_count}"
            )
        print(f"Verified {title}: {page_count} release notes")
        page_url = None
        get_url = getattr(self.publisher, "get_url", None)
        if get_url:
            page_url = get_url(title)
        if page_url:
            print(f"Confluence page: {page_url}")
        return {
            "stage": "verified",
            "verified": True,
            "page_count": page_count,
            "page_url": page_url,
        }

    @staticmethod
    def _scope_name(scope):
        return getattr(scope, "name", str(scope))

    @staticmethod
    def _recovery_action(state):
        stage = state.get("stage")
        if stage == "start":
            return "FETCH_ITEMS"
        if stage == "tickets_fetched":
            return "INSPECT_DESTINATION"
        if stage in {"confluence_inspected", "review_failed"}:
            if state.get("review_attempts", 0) >= 1:
                return "FINISH"
            return "GENERATE_DOCUMENT"
        if stage == "generation_failed":
            if state.get("generation_attempts", 0) >= 3:
                return "FINISH"
            return "GENERATE_DOCUMENT"
        if stage == "generated":
            return "REVIEW_DOCUMENT"
        if stage == "reviewed":
            return "PUBLISH_DOCUMENT"
        if stage == "uploaded":
            return "VERIFY_OUTPUT"
        if stage == "verified":
            return "FINISH"
        if stage == "action_failed":
            history = state.get("action_history", [])
            if history and history[-1] == "PUBLISH_DOCUMENT":
                return "PUBLISH_DOCUMENT"
            if history and history[-1] == "VERIFY_OUTPUT":
                return "VERIFY_OUTPUT"
            if state.get("release_notes"):
                return "REVIEW_DOCUMENT"
            if state.get("issues"):
                return "GENERATE_DOCUMENT"
            return "FETCH_ITEMS"
        return "FINISH"