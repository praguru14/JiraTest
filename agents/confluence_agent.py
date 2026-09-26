from atlassian import Confluence

import config
import logging

logger = logging.getLogger("jira_conf.confluence")


class ConfluenceAgent:

    def __init__(self):

        self.client = Confluence(
            url=config.CONFLUENCE_URL,
            username=config.JIRA_EMAIL,
            password=config.JIRA_API_TOKEN
        )

    def get_release_notes_parent(self):
        page = self._find_page("Release Notes")

        if page:
            return page.get("id")

        logger.info("Creating Release Notes parent page...")

        page = self.client.post(
            "rest/api/content",
            json={
                "type": "page",
                "title": "Release Notes",
                "space": {"key": config.CONFLUENCE_SPACE},
                "body": {
                    "storage": {
                        "value": "<h1>Release Notes</h1>",
                        "representation": "storage",
                    }
                },
            },
        )

        if isinstance(page, dict):
            return page.get("id")

        return page

    def page_exists(self, title):
        return self._find_page(title)

    def _find_page(self, title, expand=None):
        response = self.client.get(
            "rest/api/content",
            params={
                "spaceKey": config.CONFLUENCE_SPACE,
                "title": title,
                "type": "page",
                "limit": 1,
                "expand": expand,
            },
        )

        if not isinstance(response, dict):
            return None

        results = response.get("results", [])
        return results[0] if results and isinstance(results[0], dict) else None

    def get_page_note_count(self, title):

        page = self._find_page(title, expand="body.storage")

        if not page:
            return 0

        body = page.get("body", {}).get("storage", {}).get("value", "")

        # count <tr> tags and subtract header row
        rows = body.count("<tr>")

        if rows <= 1:
            return 0

        return rows - 1

    def create_or_update_page(self, title, html):

        parent_id = self.get_release_notes_parent()

        # `title` is used as provided by callers
        page = self._find_page(title, expand="version")

        if page:

            logger.info(f"{title} already exists.")
            print(f"\n{title} already exists.")

            choice = input("Update page? (Y/N): ").strip().lower()

            if choice != "y":
                print("Skipped.")
                logger.info("User chose to skip updating existing page")
                return

            version = page.get("version", {}).get("number", 0) + 1
            self.client.put(
                f"rest/api/content/{page['id']}",
                data={
                    "type": "page",
                    "title": title,
                    "version": {"number": version},
                    "body": {
                        "storage": {
                            "value": html,
                            "representation": "storage",
                        }
                    },
                },
            )
            logger.info(f"Page Updated: {title}")
            print("Page Updated.")

            return

        self.client.post(
            "rest/api/content",
            json={
                "type": "page",
                "title": title,
                "space": {"key": config.CONFLUENCE_SPACE},
                "ancestors": [{"id": parent_id}],
                "body": {
                    "storage": {
                        "value": html,
                        "representation": "storage",
                    }
                },
            },
        )
        logger.info(f"Page Created: {title}")
        print("Page Created.")