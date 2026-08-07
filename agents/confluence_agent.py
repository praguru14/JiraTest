from atlassian import Confluence

import config


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

        print("Creating Release Notes parent page...")

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

    def create_or_update_page(
        self,
        sprint_name,
        html
    ):

        parent_id = self.get_release_notes_parent()

        title = f"Release_Note_{sprint_name}"

        page = self.page_exists(title)

        if page:

            print(f"\n{title} already exists.")

            choice = input(
                "Update page? (Y/N): "
            ).strip().lower()

            if choice != "y":

                print("Skipped.")

                return

            self.client.update_page(
                page_id=page["id"],
                title=title,
                body=html,
                representation="storage"
            )

            print("Page Updated.")

            return

        self.client.create_page(
            space=config.CONFLUENCE_SPACE,
            title=title,
            body=html,
            parent_id=parent_id,
            representation="storage"
        )

        print("Page Created.")