import json
from agents.planner_agent import PlannerAgent
import logging


logger = logging.getLogger("jira_conf.debug_planner")


p = PlannerAgent()
ctx = {"stage": "start", "issues_count": 8, "sprint": "SCRUM Sprint 1"}

# raw LLM text
raw = p.llm.generate(p.system_prompt, json.dumps(ctx))
logger.debug("RAW RESPONSE:\n%s", raw)

# parsed (what main.py uses)
try:
    parsed = p.next_action(ctx)
    logger.debug("PARSED ACTION:\n%s", parsed)
except Exception as e:
    logger.exception("PARSE ERROR")
