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
