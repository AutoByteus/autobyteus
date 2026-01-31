# Context Compaction (Autobyteus)

This document describes how Autobyteus manages long-running conversations by
**compacting** history into summaries while preserving recent turns.

Compaction is part of the **agent memory** module and is used to keep the LLM
inside its context window without losing task continuity.

---

## Overview

Autobyteus builds each LLM prompt from an **Active Transcript** (per compaction
epoch). When compaction triggers, a **Compaction Snapshot** (system + memory +
recent tail) becomes the new base, and the transcript resumes appending new
turns from there.

When the **last LLM response** reports prompt tokens above the budget, the
system requests compaction and executes it **before the next LLM call**. Older
RAW_TRACE is summarized into EPISODIC memory and pruned from the active trace set.

---

## Triggers

Compaction can be triggered by:

- **Token pressure**: the last response reports prompt tokens above the input budget
- **Turn count**: after N turns (policy-driven)
- **Large tool output**: a tool result is too large for the transcript (future)
- **Manual**: an explicit compact request (future)

---

## Token Budget (Python)

Current Python implementation derives input budget from LLM config:

- `max_context_tokens` (effective): `LLMConfig.token_limit`
- `max_output_tokens`: `LLMConfig.max_tokens`
- `safety_margin`: `CompactionPolicy.safety_margin_tokens`

```
input_budget = token_limit - max_output_tokens - safety_margin
```

If `token_limit` is unset, compaction is skipped unless other triggers apply.

---

## Compaction Flow (Current)

1. **Select compaction window**: all turns except the raw tail.
2. **Summarize**: LLM summarizer produces:
   - `episodic_summary`
   - `semantic_facts`
3. **Store results**:
   - EPISODIC item written to `episodic.jsonl`
   - SEMANTIC items written to `semantic.jsonl`
4. **Prune traces**:
   - RAW_TRACE outside the tail removed from `raw_traces.jsonl`
   - Optionally archived in `raw_traces_archive.jsonl`

---

## Storage Outputs

Per agent, the default file store uses:

```
memory/agents/<agent_id>/
  raw_traces.jsonl
  raw_traces_archive.jsonl
  episodic.jsonl
  semantic.jsonl
```

---

## Current Limits / TODOs

- LLM-backed summarizer is still a pluggable interface.
- Semantic extraction is minimal and will be expanded.
