from models.local_llm import LocalLLM
import logging

logger = logging.getLogger("jira_conf.test_llm")

llm = LocalLLM()

answer = llm.generate(

    "You are a helpful assistant.",

    "Say hello in one sentence."

)

logger.info(answer)