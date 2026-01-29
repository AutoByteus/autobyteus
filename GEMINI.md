# Documentation & System Architecture

For a comprehensive "Book Catalog" of the system's design, modules, and interactions, please refer to:
**[ARCHITECTURE.md](ARCHITECTURE.md)**

This document serves as the master index for:

- **Core Engine**: Event-driven runtime, lifecycle, and processors.
- **Intelligence**: LLM module.
- **Capabilities**: Tools, Skills, and Terminal integration.
- **Coordination**: Multi-agent teams and task management.

---

# Workflow Guidelines (TDD & Documentation)

## 1. Documentation as the Map

- **Start Here**: Always begin by consulting `ARCHITECTURE.md` and the relevant design documents in `docs/`. These are the "Map" of the project.
- **Guidance**: Use these documents to understand the design intent, module boundaries, and implementation details before writing code.
- **Maintenance**: Documentation must remain "live". After finalizing any implementation, verify if the "Map" matches the territory. If the design evolved, update the corresponding documentation immediately.

## 2. Test-Driven Development (Bottom-Up)

- **TDD Approach**: Adopt a bottom-up workflow.
  1.  **Understand**: Read the docs/code to know _what_ to build.
  2.  **Test**: Write or update unit tests _first_ (or in parallel) to define the expected behavior.
  3.  **Implement**: Write the source code to pass the tests.
  4.  **Verify**: Run the tests to ensure stability.
- **Stability**: This approach ensures that every layer of the implementation is verified before moving up the stack.
- **Conventions**: Follow the existing testing structure in `tests/`. Mimic the style of neighboring test files.

## 3. Version Control

- **Atomic Commits**: Do not use `git add -A` or `git add .`. These commands stage files indiscriminately and can accidentally include unwanted changes or untracked files.
- **Explicit Staging**: Always use `git add <file_path>` to stage specific files. This ensures you are conscious of exactly what is going into each commit.

## 4. Cross-Project Impact

When modifying this library (`autobyteus`), dependent projects must re-sync to pick up changes:

- **For `autobyteus-server`**: Run `uv sync --extra dev` in the server project after making changes here.
- **Why**: The server installs `autobyteus` as an editable dependency. While `uv run` auto-rebuilds, explicit `uv sync` ensures a clean state.
- **Test**: Verify with `uv run python -c "from autobyteus.llm.models import LLMModel; print(LLMModel)"`

# Agent Testing Notes

## Why avoid bare `pytest`

- The standalone `pytest` entrypoint is installed with a hardcoded interpreter path (`#!/usr/bin/python3`), so if `PATH` hits a global install first the tests use the wrong Python and miss env packages. citeturn1search4
- Editor integrations (e.g., VS Code test explorer) sometimes fall back to the system Python even when a conda/venv is selected, leading to discovery failures. citeturn0search2
- VS Code’s test discovery has recently been reported to prepend global paths to `PYTHONPATH`, causing `pytest` to import plugins from outside the env. citeturn0search3

## What to do instead

- Always invoke tests through the environment’s interpreter: `python -m pytest`. This guarantees the `pytest` module is imported from the same Python that holds your dependencies. citeturn2search1
- For `uv`, prefer an explicit call so Gemini CLI can’t pick the wrong runtime:
  - If the env is already activated: `python -m pytest`
  - If not: `uv run python -m pytest`
- Project default env: repo-local `.venv`; activate it or call `uv run python -m pytest` when running tests.
- Example (verified): `uv run python -m pytest tests/integration_tests/llm/api/test_gemini_llm.py -q --maxfail=1 -k test_gemini_stream_user_message`
- To double-check which interpreter is in use, run `python -c "import sys; print(sys.executable)"` before testing.

## Policy for Gemini CLI agents

- When running tests locally or in CI, use the exact interpreter from the active `.venv` (`$(which python) -m pytest` or `uv run python -m pytest`).
- Never call plain `pytest` in automation; it is brittle with PATH and editor-driven launches.
- If a tool auto-generates a `pytest` command, rewrite it to `python -m pytest` with the env’s Python to avoid future surprises.
- Refactors: avoid leaving unused/backward-compatibility shims or dead code. Prefer clean, current implementations over preserving legacy branches unless explicitly required.
