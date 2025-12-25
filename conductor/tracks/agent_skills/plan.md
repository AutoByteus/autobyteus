# Implementation Plan: Agent Skills

**Goal**: Enable agents to use modular, file-based skills (directories containing `SKILL.md` and assets). Support both Preloaded (Config-based) and Dynamic (Tool-based) loading.

## Phase 1: Core Foundation (Model & Loader)
- [x] **Scaffold Directory**: Create `autobyteus/skills/` and `__init__.py`.
- [x] **Implement Model**: Create `autobyteus/skills/model.py` (`Skill` dataclass).
- [x] **Implement Loader**: Create `autobyteus/skills/loader.py` (Frontmatter parsing).
- [x] **Test Loader**: Create `tests/unit_tests/skills/test_loader.py` and verify `load_skill`.

## Phase 2: The Registry (Management)
- [x] **Implement Registry**: Create `autobyteus/skills/registry.py` (Singleton managing skills).
- [x] **Test Registry**: Create `tests/unit_tests/skills/test_registry.py` (Discovery & Path Registration).

## Phase 3: The Tool (Agent Autonomy)
- [x] **Implement Tool**: Create `autobyteus/tools/skill/load_skill.py`.
- [x] **Test Tool**: Create `tests/unit_tests/tools/test_load_skill.py`.

## Phase 4: Awareness (Processor)
- [x] **Implement Processor**: Create `autobyteus/agent/system_prompt_processor/available_skills_processor.py`.
    - Handle Metadata injection (Dynamic).
    - Handle Content injection (Preloaded).
- [x] **Test Processor**: Create `tests/unit_tests/agent/system_prompt_processor/test_available_skills_processor.py`.

## Phase 5: Deep Integration (Config & Factory)
- [x] **Update AgentConfig**: Add `skills: List[str]` field.
- [x] **Update Factory/Runtime**: Ensure Registry integration.
- [x] **E2E Test**: Create `tests/integration_tests/agent/test_agent_skills.py` (Verify full flow).