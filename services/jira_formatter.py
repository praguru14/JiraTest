class JiraFormatter:

    @staticmethod
    def get_description(issue):

        description = issue.fields.description

        if description is None:

            return ""

        return str(description)