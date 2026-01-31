import json
import re
from typing import Any

import pytest
from openai import APIConnectionError

from autobyteus.memory.compaction.compaction_result import CompactionResult
from autobyteus.memory.compaction.summarizer import Summarizer


PROMPT_TEMPLATE = """You are compressing agent memory. Summarize the following turns.
Return STRICT JSON with the schema below. Do not include extra text.

Rules:
- Output must be valid JSON only.
- All keys in the schema must be present.
- semantic_facts must contain at least 1 item. If none are explicit, infer from the turns.
- decisions/constraints/open_questions/next_steps can be empty arrays.
- If you see DECISION: or Constraint: in the turns, you MUST include them in decisions/constraints
  AND add corresponding semantic_facts.
- If a plan/idea was rejected or dropped, mark it as DISCARDED in the episodic summary.

Turns:
{turn_block}

JSON Schema:
{{
  "episodic_summary": "string",
  "semantic_facts": [
    {{ "fact": "string", "tags": ["string"], "confidence": 0.0-1.0 }}
  ],
  "decisions": ["string"],
  "constraints": ["string"],
  "open_questions": ["string"],
  "next_steps": ["string"]
}}

Example:
Turns:
(turn_0001:1) USER: Idea: store everything forever.
(turn_0001:2) ASSISTANT: We can try it.
(turn_0002:1) USER: DROPPED: store everything forever causes overflow.
(turn_0002:2) ASSISTANT: We will not use it.
(turn_0003:1) USER: DECISION: use compaction. Constraint: keep 2-turn raw tail.

JSON:
{{
  "episodic_summary": "DISCARDED: storing everything forever due to overflow. DECISION: use compaction with raw tail 2 turns.",
  "semantic_facts": [
    {{ "fact": "Use compaction with a 2-turn raw tail.", "tags": ["decision", "constraint"], "confidence": 0.8 }}
  ],
  "decisions": ["Use compaction with a 2-turn raw tail."],
  "constraints": ["Raw tail must keep 2 turns."],
  "open_questions": [],
  "next_steps": []
}}
"""


FACT_EXTRACTION_TEMPLATE = """Extract at least 1 semantic fact from the content below.
Return STRICT JSON only with the schema:
{{
  "semantic_facts": [
    {{ "fact": "string", "tags": ["string"], "confidence": 0.0-1.0 }}
  ]
}}

Content:
{content}
"""


def extract_json(payload: str) -> dict:
    match = re.search(r"\{.*\}", payload, re.DOTALL)
    if not match:
        raise AssertionError(f"No JSON object found in summarizer output: {payload}")
    return json.loads(match.group(0))


def format_trace(trace: Any) -> str:
    prefix = f"({trace.turn_id}:{trace.seq}) {trace.trace_type.upper()}:"
    if getattr(trace, "tool_name", None):
        if trace.trace_type == "tool_call":
            return f"{prefix} {trace.tool_name} {trace.tool_args}"
        if trace.trace_type == "tool_result":
            result = trace.tool_error if trace.tool_error else trace.tool_result
            return f"{prefix} {trace.tool_name} {result}"
    return f"{prefix} {trace.content}"


class RealCompactionSummarizer(Summarizer):
    def __init__(self, llm):
        self.llm = llm
        self.last_payload: dict | None = None

    def summarize(self, traces):
        turn_block = "\n".join(format_trace(trace) for trace in traces)
        prompt = PROMPT_TEMPLATE.format(turn_block=turn_block)
        data = self._call_llm_json(prompt)

        semantic_facts = data.get("semantic_facts", [])
        self._merge_marked_metadata(traces, data)
        semantic_facts = data.get("semantic_facts", [])
        if not semantic_facts:
            fallback = self._call_llm_json(
                FACT_EXTRACTION_TEMPLATE.format(content=turn_block)
            )
            semantic_facts = fallback.get("semantic_facts", [])
            data["semantic_facts"] = semantic_facts

        self.last_payload = data
        return CompactionResult(
            episodic_summary=data.get("episodic_summary", ""),
            semantic_facts=semantic_facts,
        )

    def _merge_marked_metadata(self, traces, data: dict) -> None:
        decisions, constraints = extract_marked_items(traces)
        if "decisions" not in data or not isinstance(data["decisions"], list):
            data["decisions"] = []
        if "constraints" not in data or not isinstance(data["constraints"], list):
            data["constraints"] = []

        for item in decisions:
            if item not in data["decisions"]:
                data["decisions"].append(item)
        for item in constraints:
            if item not in data["constraints"]:
                data["constraints"].append(item)

        if "semantic_facts" not in data or not isinstance(data["semantic_facts"], list):
            data["semantic_facts"] = []
        existing = [fact.get("fact", "") for fact in data["semantic_facts"]]

        for decision in decisions:
            if not any(decision in fact for fact in existing):
                data["semantic_facts"].append(
                    {"fact": decision, "tags": ["decision"], "confidence": 0.9}
                )
        for constraint in constraints:
            if not any(constraint in fact for fact in existing):
                data["semantic_facts"].append(
                    {"fact": constraint, "tags": ["constraint"], "confidence": 0.9}
                )

    def _call_llm_json(self, prompt: str) -> dict:
        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model.value,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
        except APIConnectionError:
            pytest.skip("Could not connect to LM Studio server.")

        content = response.choices[0].message.content or ""
        return extract_json(content)


def extract_marked_items(traces: list[Any]) -> tuple[list[str], list[str]]:
    decisions: list[str] = []
    constraints: list[str] = []

    for trace in traces:
        content = (trace.content or "").strip()
        if not content:
            continue

        decision_match = re.search(r"decision\\s*:\\s*(.+)", content, re.IGNORECASE)
        if decision_match:
            decision = decision_match.group(1).strip()
            if decision and decision not in decisions:
                decisions.append(decision)

        constraint_match = re.search(r"constraint\\s*:\\s*(.+)", content, re.IGNORECASE)
        if constraint_match:
            constraint = constraint_match.group(1).strip()
            if constraint and constraint not in constraints:
                constraints.append(constraint)

    return decisions, constraints
