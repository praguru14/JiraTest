"""
Application configuration.

Reads all environment variables from .env.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# -----------------------------
# Jira
# -----------------------------

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")


# -----------------------------
# Confluence
# -----------------------------

CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_SPACE = os.getenv("CONFLUENCE_SPACE")


# -----------------------------
# Local LLM
# -----------------------------

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "Qwen/Qwen2.5-0.5B-Instruct"
)