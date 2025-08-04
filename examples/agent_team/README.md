# Agent Team Examples

This directory contains example scripts that demonstrate how to build and run multi-agent and hierarchical agent teams using the `autobyteus` framework.

**Examples:**
- [Hierarchical Debate Team](#example-hierarchical-debate-team)
- [Software Development Team](#example-software-development-team)

---

## Example: Hierarchical Debate Team

This directory contains an example script, `run_debate_team.py`, that demonstrates a hierarchical, multi-agent team using the `autobyteus` framework.

### Overview

The script sets up a simulated debate on a topic provided by the user at runtime. The team has the following structure:

- **Grand_Debate (Parent Team):**
  - **DebateModerator (Coordinator Agent):** Manages the overall flow of the debate, gives turns to the teams, and concludes the session.
  - **Team_Affirmative (Sub-Team):** A team that argues *in favor* of the debate topic.
    - `Lead_Affirmative` (Coordinator)
    - `Proponent` (Worker)
  - **Team_Negative (Sub-Team):** A team that argues *against* the debate topic.
    - `Lead_Negative` (Coordinator)
    - `Opponent` (Worker)

The entire interaction is visualized in a Textual User Interface (TUI) that runs in your terminal.

### Prerequisites

1.  **Install Dependencies:** Ensure you have installed all the required packages for the project. From the project root (`autobyteus/`), run:
    ```bash
    pip install -e .
    ```

2.  **Environment Variables:** Create a `.env` file in the project root directory (`autobyteus/`) and add your LLM API keys.
    ```
    # autobyteus/.env
    OPENAI_API_KEY="sk-..."
    ANTHROPIC_API_KEY="sk-..."
    # etc.
    ```

### How to Run the Debate

All commands should be run from the project root directory (`autobyteus/`).

#### Basic Usage

To run the debate with the default LLM model (`kimi-latest`) for all agents, simply execute the script:

```bash
python examples/agent_team/run_debate_team.py
```

#### Advanced Usage: Specifying Different LLMs

You can specify different LLM models for the moderator and each of the two sub-teams. This is useful for comparing the performance and "personalities" of different models. The correct tool format (XML or JSON) is now automatically determined based on the selected LLM provider.

**Command-line Arguments:**

-   `--llm-model`: Sets the default model for any agent/team that doesn't have a specific model assigned. Defaults to `kimi-latest`.
-   `--moderator-model`: Sets the model for the `DebateModerator`.
-   `--affirmative-model`: Sets the model for both agents in `Team_Affirmative`.
-   `--negative-model`: Sets the model for both agents in `Team_Negative`.

**Example:** Run a debate where the Affirmative team uses `gpt-4o` and the Negative team uses `claude-3-opus-20240229`. The moderator will use the default model.

```bash
python examples/agent_team/run_debate_team.py \
    --llm-model qwen/qwen3-30b-a3b-2507 \
    --affirmative-model gpt-4o \
    --negative-model claude-3-opus-20240229
```

### Listing Available Models

To see a list of all supported LLM models that you can use with the arguments above, run:

```bash
python examples/agent_team/run_debate_team.py --help-models
```

---

## Example: Software Development Team

This example, `run_code_review_team.py`, demonstrates a collaborative agent team simulating a full software development lifecycle.

### Overview

The script sets up a five-agent team to handle a coding task from inception to testing:

- **ProjectManager (Coordinator Agent):** Receives a task from the user and orchestrates the entire sequential process between the other agents.
- **SoftwareEngineer (Worker Agent):** Equipped with a `FileWriter` tool, this agent writes the initial code.
- **CodeReviewer (Worker Agent):** Equipped with a `FileReader` tool, this agent reviews the code for quality.
- **TestWriter (Worker Agent):** Equipped with both `FileReader` and `FileWriter`, this agent reads the source code and writes corresponding `pytest` tests.
- **Tester (Worker Agent):** Equipped with a `BashExecutor` tool, this agent runs the tests and reports the results.

The interaction is managed in a shared local directory and visualized using the Textual TUI.

### How to Run the Team

All commands should be run from the project root directory (`autobyteus/`). The prerequisites are the same as for the Debate Team. You will also need `pytest` installed in your environment (`pip install pytest`).

#### Basic Usage

To run the team with the default LLM model (`kimi-latest`) for all agents, execute the script:

```bash
python examples/agent_team/run_code_review_team.py
```
Once the TUI starts, you can provide a prompt like: `Please write a python function that calculates the factorial of a number and save it in "factorial.py"`

The agents will write the code and test files to the `code_review_output/` directory by default.

#### Advanced Usage: Specifying Different LLMs

You can assign different LLM models to each agent to simulate a team with different skill sets or to test various models. The correct tool format (XML or JSON) is now automatically determined based on the selected LLM provider.

**Command-line Arguments:**

-   `--llm-model`: Sets the default model for any agent that doesn't have a specific model assigned.
-   `--coordinator-model`: Sets the model for the `ProjectManager`.
-   `--engineer-model`: Sets the model for the `SoftwareEngineer`.
-   `--reviewer-model`: Sets the model for the `CodeReviewer`.
-   `--test-writer-model`: Sets the model for the `TestWriter`.
-   `--tester-model`: Sets the model for the `Tester`.
-   `--output-dir`: Specifies the shared workspace directory for the agents. Defaults to `./code_review_output`.

**Example:** Run the team with `gpt-4o` as the engineer and `kimi-latest` for all other roles.

```bash
python examples/agent_team/run_code_review_team.py \
    --llm-model kimi-latest \
    --engineer-model gpt-4o
```

### Listing Available Models

To see a list of all supported LLM models for this team, run:

```bash
python examples/agent_team/run_code_review_team.py --help-models
```
