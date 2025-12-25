# Agent Skills Design (Autobyteus)

This document describes the design and implementation of **Agent Skills** in the Autobyteus Python framework.

## Philosophy: Human-Like Information Retrieval

The design of Agent Skills is fundamentally inspired by **how humans acquire and process information**. 

When a human needs to learn a new subject (e.g., "Advanced Java Programming"), they do not memorize an entire library of books instantly. Instead, they follow a hierarchical process:
1.  **Awareness**: They know a library exists and what books are in it.
2.  **Selection**: They pick a specific book (`java_expert`) relevant to their current task.
3.  **Orientation**: They read the Table of Contents (`SKILL.md`) to understand the structure and where to find specific details.
4.  **Deep Dive**: They flip to specific chapters or reference distinct files (assets/code) *only when that specific detail is needed*.

This "Just-In-Time" learning model allows agents to have infinite potential knowledge without the cognitive load (context window) of holding it all at once.

The core philosophy of this design is **Context Economy**: 
1.  **Lightweight Awareness**: The Agent is aware of *all* available skills via minimal metadata (Name + Description) in the System Prompt.
2.  **Heavyweight Loading (On-Demand)**: The massive body of a skill (instructions, examples, data) is *only* loaded into the context when explicitly triggered (dynamically).

## 1. Skill Definition: The Hierarchical "Skill as a Directory"

A **Skill** is not just a file; it is a **directory** acting as a self-contained knowledge base or toolkit. 

- **The Entry Point (`SKILL.md`)**: This file serves as the "README" or "Map" for the skill. It contains high-level instructions and *pointers* to other resources within the skill folder.
- **The Assets**: The folder can contain arbitrary files—code snippets in any language, detailed documentation, templates, or reference data.

### Structure Example
```text
skills/
  └── java_expert/
      ├── SKILL.md                 # The Entry Point
      ├── scripts/
      │   └── code_formatter.jar   # Executable asset
      ├── templates/
      │   └── SpringBootApp.java   # Code template
      └── docs/
          └── memory_model.md      # Deep-dive documentation
```

### `SKILL.md` Format
The file uses YAML Frontmatter for metadata. The body serves as the guide.

```markdown
---
name: java_expert
description: Java development expert with access to formatters and templates.
---
# Java Expert

You are a Java Expert. 
1. **Formatting**: If you need to format code, run the jar found at `./scripts/code_formatter.jar`.
2. **Boilerplate**: For new apps, read the template at `./templates/SpringBootApp.java`.
```

**Path Resolution (Context Injection)**
We do **not** use placeholders like `{{SKILL_ROOT}}`.
- **Authoring**: Authors write standard relative paths (e.g., `./scripts/...`).
- **Runtime**: When the Processor (or Tool) loads the skill, it wraps the content in a block that explicitly provides the **Root Path**.
- **Agent Behavior**: The Agent understands that `./` refers to the provided `path` attribute and constructs absolute paths for its tools.

*Injection Example:*
```xml
<skill_context name="java_expert" path="/abs/path/to/skills/java_expert">
... content of SKILL.md ...
</skill_context>
```

## 2. Core Components

### A. `Skill` Model
A data class representing a loaded skill.
- `name` (str): Unique identifier.
- `description` (str): Short summary.
- `root_path` (str): Absolute path to the skill directory (Critical for accessing assets).
- `entry_point_content` (str): The content of `SKILL.md` (loaded on demand).

### B. `SkillRegistry`
A central registry responsible for:
1.  **Discovery**: Scanning configured paths (e.g., `autobyteus/skills/`) for `SKILL.md` files.
2.  **Resolution**: Identifying the `SKILL.md` and the `root_path`.
3.  **Retrieval**: Providing access to the skill object.

### C. `LoadSkillTool`
A standard Agent Tool enabling autonomy.
- **Name**: `load_skill`
- **Arguments**: `skill_name` (str)
- **Behavior**: 
    1.  Validates the skill exists in `SkillRegistry`.
    2.  Returns a formatted string containing the `SKILL.md` content and the `root_path`.

## 3. Configuration & Integration

We support flexible skill definition via `AgentConfig`.

### A. Preloaded Skills (Static / Vertical Agents)
For specialized agents, skills are defined in the configuration. The system supports **Hybrid Loading** (Names & Paths).

- **Config**: 
    ```python
    AgentConfig(..., skills=[
        "java_expert",                  # Registered Name
        "/home/user/dev/new_skill"      # Ad-hoc Local Path
    ])
    ```
- **Startup Logic**:
    1.  **Paths**: If an entry is a path, the `SkillRegistry` dynamically loads and registers it (using the name defined in its `SKILL.md`).
    2.  **Names**: It looks up existing registered skills.
- **Result**: The `SKILL.md` content for *all* listed skills is injected into the System Prompt.

### B. Dynamic Skills (Generalist Agents)
For flexible agents, skills are discovered on demand.
- **Config**: `AgentConfig(..., skills=[])` (but `SkillRegistry` has many available)
- **Behavior**: Only metadata (Name/Description) is in the System Prompt.
- **Trigger**: 
    - The Agent, upon reading the user's natural language request (e.g., "Use the java skill"), decides to call the **`load_skill`** tool to retrieve the map.
    - No "magic shortcuts" (like `$skill`) are required; it follows standard tool usage patterns.

## 4. Execution Flow: The Universal "Deep Dive"

Regardless of *how* the skill map (`SKILL.md`) was loaded (Preloaded vs. Dynamic), the "Deep Dive" phase is identical.

1.  **Possession of the Map**: The Agent has the `SKILL.md` content (either in System Prompt or recent context).
2.  **Reading the Map**: The Agent reads: *"For template X, see ./templates/X.java"*.
3.  **The "Deep Dive" Action**: 
    - The Agent uses the standard **`read_file`** tool.
    - It constructs the absolute path using the `root_path` provided in the map.
    - `read_file(path="/abs/path/to/skill/templates/X.java")`.

### Example: Preloaded "Java Agent" (Static)
1.  **Startup**: `AgentConfig` has `skills=["java_expert"]`. System Prompt includes `SKILL.md` for `java_expert`.
2.  **User**: "Create a Spring Boot app."
3.  **Reasoning**: Agent immediately knows where the template is (from System Prompt).
4.  **Action**: Calls `read_file(path=".../templates/SpringBootApp.java")`.

### Example: Dynamic "General Assistant" (On-Demand)
1.  **Startup**: No preloaded skills. System Prompt just lists "Available: java_expert".
2.  **User**: "I need to fix a Java bug, please use the java skill."
3.  **Reasoning**: "The user requested the java skill. I should load it."
4.  **Action 1**: Calls `load_skill(name="java_expert")`.
5.  **Observation**: Receives `SKILL.md` content and root path.
6.  **Reasoning**: "The map says debugging docs are at ./docs/memory.md".
7.  **Action 2**: Calls `read_file(path=".../docs/memory.md")`.

## 5. Benefits

1.  **Infinite Extensibility**: A skill can contain entire libraries, specialized CLI tools, or encyclopedias of text, without bloating the prompt.
2.  **Polyglot Support**: A skill folder can contain Python scripts, Java JARs, Bash scripts, etc., which the agent can execute (via `run_shell_command`) if instructed by `SKILL.md`.
3.  **Context Efficiency**: The Agent only loads the "Index" (`SKILL.md`). It only pays the context cost for "Deep Dive" items if the specific task requires them.