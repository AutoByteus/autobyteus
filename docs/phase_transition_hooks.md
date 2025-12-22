# ADR: Phase Transition Hooks in Agent Framework

**Status:** Implemented

**Context:** A robust agent framework requires a clean, maintainable, and highly precise mechanism for developers to extend agent behavior at critical points in its lifecycle. This document outlines the design for a hook system based on specific phase transitions.

---

### **Feature: Implement Phase Transition Lifecycle Hooks**

**User Story:**

> **As a** developer using the AutoByteUs framework,
> **I want** to register custom logic that executes automatically when an agent makes a specific *transition* from a source phase to a target phase,
> **so that** I can precisely control and extend agent behavior (e.g., one-time setup, cleanup, validation) in a clean and decoupled way.

---

### 1. Problem Statement / Motivation

An extensible framework must allow users to inject custom logic. Initial design considerations revealed key challenges:

1.  **Ambiguity of "Setup" Logic:** A common need is to run a task exactly once after an agent initializes. A naive hook tied to the `IDLE` phase is insufficient, as the agent re-enters `IDLE` after every task, causing the hook to run multiple times.
2.  **Brittleness of Implementation-Detail Hooks:** Tying a setup hook to the last known step of the initialization process (e.g., `INITIALIZING_PROMPT`) is brittle. If the bootstrap sequence changes in the future, the hook will break.
3.  **Lack of Precision:** A simple hook that only knows the phase being *entered* cannot differentiate between different paths to that phase, limiting its utility for more complex stateful logic.

This feature solves these problems by creating a hook system centered on the **phase transition** itself, providing maximum precision while keeping the agent's core state machine simple and robust.

### 2. Proposed Solution

The implemented solution is a hook system where each hook is self-describing, specifying the exact phase transition it targets.

1.  **Introduce `BOOTSTRAPPING` Phase:** To provide a clear and stable lifecycle event, the various initialization steps (`queue_init`, `prompt_processing`, etc.) are now grouped under a single, unified `AgentOperationalPhase.BOOTSTRAPPING`. The agent remains in this phase for the entire duration of its setup.
2.  **Define `BasePhaseHook`:** A new abstract base class, `autobyteus.agent.hooks.BasePhaseHook`, is the foundation of the system. Subclasses are required to define `source_phase` and `target_phase` properties. This makes each hook self-contained and explicit about its trigger condition. For example, a one-time setup hook will target the `BOOTSTRAPPING` -> `IDLE` transition.
3.  **Update `AgentConfig`:** The `AgentConfig` accepts a simple list of hook instances (`phase_hooks: List[BasePhaseHook]`). The framework does not need to categorize the hooks, as each hook defines its own trigger.
4.  **Integrate Hook Execution:** The `AgentPhaseManager` is responsible for executing hooks. During a phase transition from an `old_phase` to a `new_phase`, it iterates through the configured list of hooks and executes any where `hook.source_phase == old_phase` and `hook.target_phase == new_phase`. This logic is sandboxed to ensure that a faulty hook logs an error but does not crash the agent.

### 3. Acceptance Criteria (Definition of Done)

1.  **[Hook Definition]** `autobyteus/autobyteus/agent/hooks.py` defines `BasePhaseHook`, which requires subclasses to implement `source_phase` and `target_phase` properties and an `async def execute(self, context)` method.
2.  **[Configuration]** The `autobyteus.agent.context.AgentConfig` class includes a `phase_hooks: List[BasePhaseHook]` parameter in its `__init__` method to accept a flat list of hook instances.
3.  **[Phase Definition]** The `autobyteus.agent.context.phases.AgentOperationalPhase` enum includes a `BOOTSTRAPPING` phase.
4.  **[Execution Logic]** The `autobyteus.agent.context.AgentPhaseManager`'s `_transition_phase` method correctly executes hooks:
    *   It iterates through the list of all registered hooks from the agent's config.
    *   It performs a check to execute only those hooks where the hook's `source_phase` and `target_phase` match the current transition.
    *   Execution is wrapped in a `try...except` block to prevent a single hook failure from halting the agent.
5.  **[Lifecycle Integration]** The agent's lifecycle is clear and robust:
    *   The agent enters the `BOOTSTRAPPING` phase at the start of its initialization.
    *   Upon successful bootstrap, the agent makes a single, well-defined transition from `BOOTSTRAPPING` to `IDLE`.
    *   A hook registered for `(BOOTSTRAPPING -> IDLE)` executes exactly once.
    *   After completing a recurring task, the agent transitions from a processing phase back to `IDLE`. A hook for `(BOOTSTRAPPING -> IDLE)` does not trigger during this recurring loop.
6.  **[External Notification]** The event system is consistent, defining and emitting `EventType.AGENT_PHASE_BOOTSTRAPPING_STARTED` and `EventType.AGENT_PHASE_IDLE_ENTERED` at the appropriate times.
