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

        page = self.client.get_page_by_title(
            config.CONFLUENCE_SPACE,
            "Release Notes"
        )

        if page:
            return page["id"]

        logger.info("Creating Release Notes parent page...")

        page = self.client.create_page(
            space=config.CONFLUENCE_SPACE,
            title="Release Notes",
            body="<h1>Release Notes</h1>",
            representation="storage"
        )

        return page["id"]

    def page_exists(self, title):

        page = self.client.get_page_by_title(
            config.CONFLUENCE_SPACE,
            title
        )

        return page

    def get_page_note_count(self, title):

        page = self.page_exists(title)

        if not page:
            return 0

        # fetch full page content
        page_id = page["id"]

        page_full = self.client.get_page_by_id(
            page_id,
            expand='body.storage'
        )

        body = page_full.get("body", {}).get("storage", {}).get("value", "")

        # count <tr> tags and subtract header row
        rows = body.count("<tr>")

        if rows <= 1:
            return 0

        return rows - 1

    def create_or_update_page(self, title, html):

        parent_id = self.get_release_notes_parent()

        # `title` is used as provided by callers
        page = self.page_exists(title)

        if page:

            logger.info(f"{title} already exists.")
            print(f"\n{title} already exists.")

            choice = input("Update page? (Y/N): ").strip().lower()

            if choice != "y":
                print("Skipped.")
                logger.info("User chose to skip updating existing page")
                return

            try:
                self.client.update_page(
                    page_id=page["id"],
                    title=title,
                    body=html,
                    representation="storage"
                )
                logger.info(f"Page Updated: {title}")
                print("Page Updated.")
            except Exception as e:
                logger.exception(f"Failed to update page {title}: {e}")

            return

        try:
            self.client.create_page(
                space=config.CONFLUENCE_SPACE,
                title=title,
                body=html,
                parent_id=parent_id,
                representation="storage"
            )
            logger.info(f"Page Created: {title}")
            print("Page Created.")
        except Exception as e:
            logger.exception(f"Failed to create page {title}: {e}")