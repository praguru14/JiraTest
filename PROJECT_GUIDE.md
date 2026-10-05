# JiraConf AI Project Guide

JiraConf AI collects completed Jira tickets from a sprint, creates customer-friendly release notes with an LLM, reviews those notes, and publishes them as an HTML table to Confluence.

## What the project does

The application automates this workflow:

1. Connect to Jira.
2. Select a board and sprint.
3. Fetch tickets whose status is `Done`.
4. Check whether a matching Confluence release-notes page exists.
5. Ask an LLM to create one release-note object per ticket.
6. Ask an LLM to review the generated notes.
7. Build an HTML page from the notes.
8. Create or update the Confluence page.

The main entry point is `main.py`.

## High-level architecture

```text
main.py
  |
  +-- JiraAgent ------------ Jira REST API
  |       |
  |       +-- boards
  |       +-- sprints
  |       +-- Done tickets
  |
  +-- ConfluenceAgent ------ Confluence REST API
  |       |
  |       +-- find page
  |       +-- count existing notes
  |       +-- create/update page
  |
  +-- WorkflowAgent
          |
          +-- PlannerAgent ------ chooses the next workflow action
          +-- ReleaseAgent ------ creates release notes
          +-- ReviewerAgent ------ reviews release notes
          +-- HTMLBuilder -------- builds the Confluence HTML
          +-- LLMAdapter --------- selects Ollama, Gemini, remote, or local LLM
```

## Runtime flow

### 1. Application startup

`main.py` creates these objects:

- `JiraAgent`
- `ReleaseAgent`
- `ConfluenceAgent`
- `PlannerAgent`
- `ReviewerAgent`

It then reads command-line arguments and configures logging to both the console and `agent.log`.

### 2. Board and sprint selection

The selected board is found by its Jira board ID. Sprints are returned by Jira in Jira's own order. The numeric `--sprint-index` is a 1-based position in that returned list, not necessarily the number in the sprint name.

For example, Jira may return:

```text
1. PG2 Sprint 2
2. PG2 Sprint 1
```

The safest option is `--sprint-name`:

```powershell
python main.py --board-id 2 --sprint-name "PG2 Sprint 2"
```

### 3. Jira ticket collection

`JiraAgent.get_done_issues()` runs a JQL query equivalent to:

```text
project = PG2
AND Sprint = "PG2 Sprint 2"
AND status = Done
```

The result is limited to 100 tickets.

### 4. Existing-page check

The application looks for a page titled:

```text
Release_Note_<sprint name>
```

For example:

```text
Release_Note_PG2 Sprint 2
```

It counts table rows on the existing page, excluding the header row. If the page has at least as many notes as the number of completed Jira tickets, the run skips that sprint unless `--force` is used.

This is a count-based check. It does not compare every Jira ticket number with every row on the Confluence page.

### 5. Planner workflow

For a sprint that needs processing, `WorkflowAgent` runs a bounded loop. The planner receives a compact state object and returns an action such as:

- `FETCH_ITEMS`
- `INSPECT_DESTINATION`
- `GENERATE_DOCUMENT`
- `REVIEW_DOCUMENT`
- `PUBLISH_DOCUMENT`
- `VERIFY_OUTPUT`
- `FINISH`

The planner chooses the next action from the current goal, state, action history,
tool results, and errors. The controller still enforces prerequisites so the
agent cannot upload unreviewed notes or finish before publishing is verified.

One successful sequence is:

```text
FETCH_ITEMS
  -> INSPECT_DESTINATION
  -> GENERATE_DOCUMENT
  -> REVIEW_DOCUMENT
  -> PUBLISH_DOCUMENT
  -> VERIFY_OUTPUT
  -> FINISH
```

The agent can choose a different valid sequence when recovery is needed. It has
a maximum of 12 steps, keeps a short action history, and retries failed tools
through guarded recovery decisions.

### 6. Release-note generation

`ReleaseAgent` sends each Jira ticket to the configured LLM using `prompts/release_prompt.txt`.

Each response must be one JSON object with this shape:

```json
{
  "label": "Feature",
  "ticket_number": "PG2-24",
  "description": "Customer-friendly description."
}
```

The current validator requires:

- `label` exists and is a non-empty string
- `ticket_number` exists
- `description` exists

Labels are intentionally open-ended. Values such as `Feature`, `Bug Fix`, `Improvement`, `Security`, or `None` are accepted.

If the model omits a description, the application falls back to the Jira summary or description. Each ticket can be retried when parsing or validation fails.

### 7. Review

`ReviewerAgent` sends the complete release-note array to the LLM using `prompts/reviewer_prompt.txt`.

The expected response is:

```json
{
  "valid": true,
  "errors": [],
  "suggestions": []
}
```

The workflow requires `valid` to be `true`. If a local model incorrectly rejects notes that have the required deterministic schema, the workflow uses a local schema fallback before upload.

### 8. HTML generation

`HTMLBuilder` loads `templates/release_notes.html` and replaces:

- `{{SPRINT_NAME}}` with the sprint name
- `{{TABLE_ROWS}}` with one table row per release note

The resulting HTML contains these columns:

- S.No
- Label
- Ticket Number
- Description

### 9. Confluence publishing

`ConfluenceAgent.create_or_update_page()` does one of two things:

- If the page does not exist, it creates the page under the `Release Notes` parent page.
- If the page exists, it asks for confirmation and updates the page version when the answer is `Y`.

When updating an existing page, the Confluence client must receive the payload through `data=`. The installed `atlassian-python-api` client does not use `json=` for `PUT` requests.

## Command-line usage

Process a sprint by its Jira-returned position:

```powershell
python main.py --board-id 2 --sprint-index 1
```

Process a sprint by its exact name:

```powershell
python main.py --board-id 2 --sprint-name "PG2 Sprint 2"
```

Force regeneration even when the existing page appears up to date:

```powershell
python main.py --board-id 2 --sprint-name "PG2 Sprint 2" --force
```

Enable debug logging:

```powershell
python main.py --board-id 2 --sprint-name "PG2 Sprint 2" --verbose
```

Run automatic processing for pending sprints on the first board:

```powershell
python main.py --auto
```

## Configuration

Configuration is loaded from `.env` by `config.py`.

Typical settings are:

```dotenv
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-atlassian-api-token
JIRA_PROJECT_KEY=PG2

CONFLUENCE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_SPACE=RN

LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

Never commit `.env` or expose `JIRA_API_TOKEN`. If a token has been shared publicly or pasted into logs, rotate it in Atlassian and replace it locally.

## LLM providers

`models/llm_adapter.py` selects the provider using `LLM_PROVIDER`:

- `ollama`: uses `models/ollama_llm.py` and the local Ollama HTTP API
- `gemini`: uses `models/gemini_llm.py`
- `remote`: uses `models/remote_llm.py`
- any other value, including the default, uses `models/local_llm.py`

For Ollama, the daemon must be running and the configured model must be installed:

```powershell
ollama serve
ollama list
```

The application calls Ollama at:

```text
http://localhost:11434/api/chat
```

The client requests JSON output and uses a low temperature for more predictable structured responses.

## Important project files

| File | Purpose |
| --- | --- |
| `main.py` | CLI entry point and sprint pre-check |
| `config.py` | Loads environment configuration |
| `agents/jira_agent.py` | Jira boards, sprints, and Done-ticket queries |
| `agents/confluence_agent.py` | Confluence page lookup, creation, and update |
| `agents/workflow_agent.py` | Goal-driven agent loop, tool guards, recovery, and verification |
| `agents/planner_agent.py` | LLM-based next-action selection |
| `agents/release_agent.py` | Per-ticket release-note generation and validation |
| `agents/reviewer_agent.py` | Release-note review |
| `models/llm_adapter.py` | Provider selection |
| `models/ollama_llm.py` | Ollama API client |
| `models/local_llm.py` | Lazy-loaded Hugging Face model |
| `services/html_builder.py` | Converts notes to HTML |
| `services/json_service.py` | Parses JSON returned by an LLM |
| `prompts/planner_prompt.txt` | Planner instructions |
| `prompts/release_prompt.txt` | Release-note instructions |
| `prompts/reviewer_prompt.txt` | Reviewer instructions |
| `templates/release_notes.html` | Confluence page template |
| `agent.log` | Rotating debug and workflow log |

## Common problems

### Ollama connection refused

Symptom:

```text
HTTPConnectionPool(host='localhost', port=11434): Max retries exceeded
```

Cause: Ollama is not running or is not listening on the configured URL.

Fix:

```powershell
ollama serve
```

Then verify the model name in `.env` matches a model shown by `ollama list`.

### Release note failed to parse

The message can refer to either invalid JSON or schema validation. The response must be a JSON object with non-empty `label`, `ticket_number`, and `description` fields.

The release prompt asks for JSON-only output, and Ollama is called with `format: "json"`.

### Existing page was skipped

If the page contains at least as many table rows as completed Jira tickets, the application assumes it is up to date. Use `--force` to regenerate and upload it.

### Update page body missing

For an existing Confluence page, the update request must use the `data` argument of the installed `atlassian-python-api` client. Using `json` causes Confluence to receive an empty request body.

### Upload was not attempted

Check the workflow log. Upload only occurs after successful review. If review fails, the workflow may regenerate once and then finish without uploading.

## Development notes

The project is intentionally modular:

- API access lives in agent classes.
- LLM selection is isolated behind `LLMAdapter`.
- Prompts are external text files.
- HTML is externalized in a template.
- Workflow decisions, tool guards, recovery, and verification are centralized in `WorkflowAgent`.

When changing the release-note schema, update all three places together:

1. `prompts/release_prompt.txt`
2. `ReleaseAgent._validate_note()`
3. `WorkflowAgent._notes_have_valid_schema()`

When changing the Confluence payload, verify the method signature of the installed `atlassian-python-api` package because `POST` and `PUT` do not necessarily accept the same body arguments.
