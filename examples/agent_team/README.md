# Agent Team Examples

This directory contains example scripts that demonstrate how to build and run multi-agent and hierarchical agent teams using the `autobyteus` framework.

The examples are categorized into two subdirectories based on the team's task notification mode:

-   `manual_notification/`: In this mode, the coordinator agent is explicitly prompted to manage the workflow by sending messages to other agents to start their tasks. This demonstrates direct, agent-driven orchestration.
-   `event_driven/`: In this mode, the team is configured to be `SYSTEM_EVENT_DRIVEN`. The coordinator's only job is to publish a plan to the `TaskPlan`. The framework then automatically monitors the board and sends notifications to agents when their tasks become runnable.

**Examples:**
- [Hierarchical Debate Team (Manual Notification)](#example-hierarchical-debate-team)
- [Software Development Team (Manual vs. Event-Driven)](#example-software-development-team)
- Other examples demonstrating basic and multi-specialist teams.

---

## Example: Hierarchical Debate Team

This example, located in `manual_notification/run_debate_team.py`, demonstrates a hierarchical, multi-agent team using manual, agent-driven notifications.

### Overview

The script sets up a simulated debate on a topic provided by the user at runtime. The team has the following structure:

- **Grand_Debate (Parent Team):**
  - **DebateModerator (Coordinator Agent):** Manages the overall flow of the debate by manually sending messages to the sub-teams to give them turns.
  - **Team_Affirmative (Sub-Team):** A team that argues *in favor* of the debate topic.
  - **Team_Negative (Sub-Team):** A team that argues *against* the debate topic.

The entire interaction is visualized in a Textual User Interface (TUI) that runs in your terminal.

### How to Run

All commands should be run from the project root directory (`autobyteus/`). See the script's `--help` for command-line arguments to specify LLM models.

```bash
python examples/agent_team/manual_notification/run_debate_team.py
```

---

## Example: Software Development Team

This example demonstrates a collaborative agent team simulating a full software development lifecycle. It is available in two versions to showcase both notification protocols.

- **Manual Notification:** `manual_notification/run_software_engineering_team.py`
- **System Event-Driven:** `event_driven/run_software_engineering_team.py`

### Overview

The script sets up a four-agent team to handle a coding task from inception to testing:

- **ProjectManager (Coordinator Agent):** Receives a task from the user and creates a plan.
- **SoftwareEngineer (Worker Agent):** Writes the initial code and the corresponding tests.
- **CodeReviewer (Worker Agent):** Reviews the code and tests for quality.
- **Tester (Worker Agent):** Runs the tests and reports the results.

In the **manual** version, the ProjectManager is responsible for sending a message to each agent to kick off their task. In the **event-driven** version, the ProjectManager only publishes the plan, and the system handles all subsequent notifications automatically.

### How to Run the Team

All commands should be run from the project root directory (`autobyteus/`). You will need `pytest` installed in your environment (`pip install pytest`).

#### Run the Manual Notification Version

```bash
python examples/agent_team/manual_notification/run_software_engineering_team.py
```

#### Run the Event-Driven Version

```bash
python examples/agent_team/event_driven/run_software_engineering_team.py
```

Once the TUI starts for either version, you can provide a prompt like: `Please write a python function that calculates the factorial of a number, save it in "factorial.py", and write a test for it in "test_factorial.py"`

### Advanced Usage: Specifying Different LLMs

You can assign different LLM models to each agent to simulate a team with different skill sets or to test various models. This works for both the manual and event-driven scripts.

**Command-line Arguments:**

-   `--llm-model`: Sets the default model for any agent that doesn't have a specific model assigned.
-   `--coordinator-model`: Sets the model for the `Project Manager`.
-   `--engineer-model`: Sets the model for the `Software Engineer`.
-   `--reviewer-model`: Sets the model for the `Code Reviewer`.
-   `--tester-model`: Sets the model for the `Tester`.
-   `--output-dir`: Specifies the shared workspace directory for the agents. Defaults to `./code_review_output`.
-   `AUTOBYTEUS_STREAM_PARSER`: Set to `xml` or `json` to override tool-call formatting/parsing for all agents.

**Example:** Run the team with `gpt-4o` as the engineer and `kimi-latest` for all other roles.

```bash
python examples/agent_team/manual_notification/run_software_engineering_team.py \
    --llm-model kimi-latest \
    --engineer-model gpt-4o

python examples/agent_team/event_driven/run_software_engineering_team.py \
    --llm-model kimi-latest \
    --engineer-model gpt-4o
```

**Example:** Run a team where each member uses a different LLM. This is useful for testing a "diverse" team composition.

```bash
AUTOBYTEUS_STREAM_PARSER=xml python examples/agent_team/event_driven/run_software_engineering_team.py \
    --coordinator-model qwen/qwen3-next-80b:lmstudio@192.168.2.158:1234 \
    --engineer-model qwen/qwen3-next-80b:lmstudio@192.168.2.158:1234 \
    --reviewer-model qwen/qwen3-next-80b:lmstudio@192.168.2.158:1234 \
    --tester-model qwen/qwen3-next-80b:lmstudio@192.168.2.158:1234
```

python examples/agent_team/event_driven/run_software_engineering_team.py \
    --coordinator-model google/gemma-3n-e4b:lmstudio@192.168.2.126:1234 \
    --engineer-model google/gemma-3n-e4b:lmstudio@192.168.2.126:1234 \
    --reviewer-model google/gemma-3n-e4b:lmstudio@192.168.2.126:1234 \
    --tester-model google/gemma-3n-e4b:lmstudio@192.168.2.126:1234

### Listing Available Models

To see a list of all supported LLM models for these teams, run either script with `--help-models`:

```bash
python examples/agent_team/manual_notification/run_software_engineering_team.py --help-models
```
