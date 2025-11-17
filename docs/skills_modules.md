# Filesystem Skills & Module Protocol

This document explains how to expose capabilities to an Autobyteus agent by dropping self-contained skill folders onto the filesystem. Each skill acts like a small project that contains:

- `skill.md` – the high-level catalog that enters the agent system prompt
- Optional supporting assets (schema files, READMEs, example transcripts, module runners, etc.) referenced from `skill.md`

The agent learns what files exist by reading `skill.md`. The LLM then decides when to load additional assets (for example, a module schema) and when to issue a `[RUN_MODULE] … [/RUN_MODULE]` command.

## Folder Layout

```
skills/
  image_generation/
    skill.md
    modules/
      image_gen/module.json
      image_gen/run.py
    examples/
      prompt_styles.md
  research_assistant/
    skill.md
```

Only `skill.md` is mandatory. It should describe:

1. What the skill is for
2. Which files or modules exist inside the folder
3. How to call any modules (e.g., names/arguments for `[RUN_MODULE]`)
4. Any few-shot transcripts or world knowledge the LLM should reference

Because the LLM sees the overview first, it can progressively load deeper context—very similar to a human skimming a book’s table of contents before jumping to a chapter.

## Wiring Skills Into an Agent

```python
from autobyteus.agent.context import AgentConfig

config = AgentConfig(
    name="FilesytemAgent",
    role="Autonomous operator",
    description="Uses skill folders from ./skills",
    llm_instance=my_llm,
    system_prompt="You are a helpful agent. {{skills}}",
    skill_file_paths=["skills/image_generation", "skills/research_assistant"],
)
```

- `skill_file_paths` accepts directories or direct paths to `skill.md`. Multiple entries are supported.
- When a path is provided, the new `SkillInjectorProcessor` loads each `skill.md` and injects a formatted block into the `{{skills}}` placeholder (or appends it to the system prompt).
- Because skills are in use, the module protocol turns on automatically. The `ProviderAwareToolUsageProcessor` watches for `[RUN_MODULE]` blocks before falling back to provider-specific tool parsing.

## Calling Modules

Skills describe how to call modules using the text-only protocol:

```
[RUN_MODULE]
{"name": "image_gen", "args": {"prompt": "sleepy teapot", "style": "charcoal"}}
[/RUN_MODULE]
```

At runtime:

1. The agent extracts the block and resolves `image_gen` from the tool registry.
2. `FilesystemModuleTool` streams the JSON args to the skill’s `run.py` (stdin) and expects JSON on stdout.
3. The agent wraps the response in `[MODULE_RESULT] … [/MODULE_RESULT]` and feeds it back to the LLM, which can continue reasoning or call more modules.

If a skill doesn’t need to call modules for a given task, the LLM can simply stay in text mode; nothing is pre-loaded until it decides to act.

## Writing `module.json`

Although skills describe their modules textually, the runtime still needs a manifest when execution is requested. Each `module.json` should specify:

```json
{
  "name": "image_gen",
  "description": "Generate images via local diffusion pipeline",
  "command": ["python", "run.py"],
  "working_dir": "modules/image_gen",
  "arguments": [
    {"name": "prompt", "type": "string", "description": "Scene description", "required": true},
    {"name": "style", "type": "string", "description": "Art style", "required": false}
  ]
}
```

When the LLM calls `[RUN_MODULE]`, the agent loads the manifest on demand and enforces the schema in the usual `BaseTool` pipeline.

## Testing a Skill

1. Write `skill.md` with clear instructions and pointers to optional files.
2. Provide a CLI entry point or script that accepts JSON via stdin and returns JSON via stdout.
3. Manually invoke the script to ensure it behaves correctly:
   ```bash
   echo '{"args": {"prompt": "test"}}' | python skills/image_generation/modules/image_gen/run.py
   ```
4. Run the targeted parser tests (example below) to ensure `[RUN_MODULE]` handling hasn’t regressed:
   ```bash
   pytest tests/unit_tests/tools/usage/parsers/test_filesystem_module_usage_parser.py
   ```

With this structure, adding a new skill is as easy as dropping a folder into `skills/`—the prompt stays compact, the LLM sees a catalog of capabilities, and it loads deeper context only when it needs it.
