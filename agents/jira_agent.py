from jira import JIRA

import config


class JiraAgent:

    def __init__(self):

        self.jira = JIRA(
            server=config.JIRA_URL,
            basic_auth=(
                config.JIRA_EMAIL,
                config.JIRA_API_TOKEN
            )
        )

    def get_projects(self):

        return self.jira.projects()

    def get_boards(self):

        return self.jira.boards()

    def get_sprints(self, board_id):

        return self.jira.sprints(board_id)

    def get_done_issues(self, sprint_name):

        jql = f'''
            project = {config.JIRA_PROJECT_KEY}
            AND Sprint = "{sprint_name}"
            AND status = Done
        '''

        return self.jira.search_issues(
            jql,
            maxResults=100
        )