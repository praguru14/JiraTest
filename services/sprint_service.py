class SprintService:

    def __init__(
        self,
        jira_agent,
        confluence_agent
    ):

        self.jira = jira_agent
        self.conf = confluence_agent

    def choose_sprints(self):

        boards = self.jira.get_boards()

        import logging
        logger = logging.getLogger("jira_conf.sprint_service")

        logger.info("Available Boards:")

        for board in boards:

            logger.info(f"{board.id}. {board.name}")

        board_id = int(
            input(
                "\nBoard Id : "
            )
        )

        sprints = self.jira.get_sprints(
            board_id
        )

        pending = []

        logger.debug("Enumerating sprints and checking pending status")

        for index, sprint in enumerate(
            sprints,
            start=1
        ):

            title = f"Release_Note_{sprint.name}"

            exists = self.conf.page_exists(
                title
            )

            if exists:
                logger.info(f"{index}. {sprint.name} ✓")
            else:
                logger.info(f"{index}. {sprint.name}")
                pending.append(sprint)

        print()
        print("1. Generate One Sprint")
        print("2. Generate Pending")
        print("3. Exit")

        choice = input("\nChoice : ")

        if choice == "1":

            sprint = int(
                input(
                    "\nSprint Number : "
                )
            )

            return [
                sprints[sprint - 1]
            ]

        elif choice == "2":

            return pending

        return []