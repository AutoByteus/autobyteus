# Implementation Plan

## Scope Classification

- Classification: `Small`
- Reasoning:
  - Changes are localized to search provider modules, tests, and example messaging.
  - No persistence/schema changes.
  - `search_web` tool API remains unchanged.

## Plan Maturity

- Current Status: `Simulation-Validated`
- Notes:
  - Runtime paths (explicit provider, fallback provider, error path) are covered in call-stack artifact.

## Solution Sketch

- In scope:
  - Add `vertex_ai_search` provider to Python search module.
  - Add `VertexAISearchStrategy` based on Vertex AI Search `searchLite`.
  - Remove active `google_cse` support and strategy/tests.
  - Keep `serper` and `serpapi` behavior unchanged.
  - Update integration/unit tests and deep-research example provider summary.
- Files:
  - `autobyteus/tools/search/providers.py`
  - `autobyteus/tools/search/factory.py`
  - `autobyteus/tools/search/__init__.py`
  - `autobyteus/tools/search/vertex_ai_search_strategy.py`
  - `autobyteus/tools/search/google_cse_strategy.py` (remove)
  - `autobyteus/tools/search_tool.py`
  - `tests/unit_tests/tools/search/test_search_client_factory.py`
  - `tests/integration_tests/tools/search/test_vertex_ai_search_strategy.py`
  - `tests/integration_tests/tools/search/test_google_cse_strategy.py` (remove)
  - `tests/integration_tests/tools/test_search_tool.py`
  - `examples/run_deep_research_agent.py`

## Use Case Simulation Gate

| Use Case | Simulation Location | Primary Path Covered | Fallback/Error Covered | Status |
| --- | --- | --- | --- | --- |
| Explicit `vertex_ai_search` provider | `docs/simulated-runtime-call-stack.md` | Yes | Yes | Passed |
| Fallback to Vertex after Serper/SerpApi | `docs/simulated-runtime-call-stack.md` | Yes | Yes | Passed |
| Removed `google_cse` provider selection | `docs/simulated-runtime-call-stack.md` | Yes | Yes | Passed |

## Go / No-Go

- Decision: `Go`

## Sequence

1. Update provider enum and new strategy.
2. Wire factory and exports.
3. Update tests for new/removed provider behavior.
4. Update example search-provider summary.
5. Run targeted `python -m pytest` suites.
