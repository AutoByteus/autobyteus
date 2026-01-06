# Tool Schema and Configuration Design and Implementation

**Date:** 2026-01-06
**Status:** Live

## 1. Overview

Tools in Autobyteus support two distict data ingestion pathways, each requiring a well-defined schema:

1.  **Runtime Arguments**: Arguments passed by the LLM when it invokes a tool (e.g., source code content for a `write_file` tool).
2.  **Instantiation Configuration**: Configuration parameters passed when a tool instance is created (e.g., API keys, result limits).

This document details the unified design for defining, generating, and using schemas for both scenarios.

---

## 2. Goals

- **Discoverability**: Provide clear, accessible schemas so users and LLMs understand exactly what a tool accepts.
- **Consistency**: Use a unified underlying schema model (`ParameterSchema`) for both runtime args and static config.
- **Ease of Use**: Auto-generate schemas from Python type hints and standard `pydantic.Field` definitions.
- **Flexibility**: Allow tools to be simple (zero-config) or complex (rich validation) without changing the framework core.
- **Validation**: Enable data validation at both instantiation time (config) and runtime (arguments).

**Non-goals**:

- Enforcing a universal config format beyond the internal `ParameterSchema`.
- Automatically converting runtime arguments into configuration settings.

---

## 3. Core Architecture

### 3.1 `ParameterSchema` and `ParameterDefinition`

_File_: `autobyteus/utils/parameter_schema.py`

These classes form the backbone of the schema system:

- **`ParameterDefinition`**: Defines a single field (name, type, description, default, constraints).
- **`ParameterSchema`**: A collection of definitions with logic for validation and serialization (to JSON/XML).

It supports primitive types (`STRING`, `INTEGER`, `FLOAT`, `BOOLEAN`), `ENUM`s, and nested `OBJECT`s/`ARRAY`s.

### 3.2 `ToolDefinition` and Discovery

_File_: `autobyteus/tools/registry/tool_definition.py`

The `ToolRegistry` stores `ToolDefinition` objects which hold providers for both schemas:

- `argument_schema`: Runtime LLM arguments.
- `config_schema`: Instantiation-time configuration.

These properties are **lazily generated and cached** to minimize overhead at startup.

---

## 4. Part I: Runtime Argument Schema

Argument schemas tell the LLM how to call a tool. They are generated automatically from Python code.

### 4.1 The `@tool` Decorator

_File_: `autobyteus/tools/functional_tool.py`

The primary way to define a tool is via numbers the `@tool` decorator. It introspects the decorated function's signature (`inspect.signature`) to build a `ParameterSchema`.

### 4.2 Type Mapping

Python type hints are mapped to internal `ParameterType`s:

| Python Type | ParameterType | JSON Schema |
| ----------- | ------------- | ----------- |
| `str`       | STRING        | string      |
| `int`       | INTEGER       | integer     |
| `float`     | FLOAT         | number      |
| `bool`      | BOOLEAN       | boolean     |
| `dict`      | OBJECT        | object      |
| `list`      | ARRAY         | array       |
| `Enum`      | ENUM          | string      |

### 4.3 Pydantic Field Support

To provide rich metadata without writing boilerplate, we support `pydantic.Field` in function signatures.

**Mechanism**:
The signature parser detects `pydantic.fields.FieldInfo` in default values.

- **Description**: Extracted for the LLM schema.
- **Default Value**: Used as the parameter default.
- **Requiredness**: Implicitly required if `Field(...)` or `Field()` is used.

**Example**:

```python
from pydantic import Field
from autobyteus.tools.functional_tool import tool

@tool
def create_user(
    username: str = Field(..., description="Unique identifier for the user"),
    is_admin: bool = Field(False, description="Grant admin privileges")
):
    ...
```

### 4.4 Flow: From Python to LLM Prompt

1.  **Developer**: Writes `@tool` function with optional `Field`s.
2.  **Decorator**: Parses signature into `ParameterSchema`.
3.  **Registry**: Stores it in `ToolDefinition`.
4.  **Formatters**:
    - `DefaultXmlSchemaFormatter`: Converts schema to `<tool>` XML.
    - `DefaultJsonSchemaFormatter`: Converts schema to JSON for OpenAI.
5.  **LLM**: Sees the formatted schema in the system prompt.

### 4.5 Custom Overrides

For complex requirements (e.g., custom sentinel tag instructions like `write_file`'s `__START_CONTENT__`), specific tools can bypass default generation by registering a **Custom Formatter** in the `ToolFormattingRegistry`.

---

## 5. Part II: Instantiation Configuration Schema

Configuration schemas tell the developer (or application builder) how to configure a tool instance.

### 5.1 `ToolConfig`

_File_: `autobyteus/tools/tool_config.py`

A simple wrapper `ToolConfig(params: Dict[str, Any])` used to pass raw configuration data into tool constructors.

### 5.2 Defining Configuration

Tools implement the `get_config_schema()` class method to declare their options.

**Example**:

```python
class SearchTool(BaseTool):
    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="max_results",
            param_type=ParameterType.INTEGER,
            description="Maximum number of search results",
            required=False,
            default_value=5,
            min_value=1,
            max_value=50,
        ))
        return schema
```

### 5.3 Passing Configuration

Configuration is passed during instantiation:

**1. Direct Instantiation**:

```python
search_tool = SearchTool(config=ToolConfig({"max_results": 5}))
```

**2. Via Registry**:

```python
tool = registry.create_tool("SearchTool", config=ToolConfig({"max_results": 5}))
```

### 5.4 Validation Strategy

Validation is optional but supported via `ParameterSchema.validate_config`.

**Recommended Pattern**:

```python
def __init__(self, config: Optional[ToolConfig] = None):
    super().__init__(config)
    schema = self.get_config_schema()
    if schema and config:
        is_valid, errors = schema.validate_config(config.params)
        if not is_valid:
            raise ValueError(f"Invalid config: {errors}")
```

---

## 6. Best Practices for Tool Authors

1.  **Separation of Concerns**: Use `get_config_schema()` for _static_ setup (keys, limits) and `@tool` arguments for _dynamic_ LLM inputs.
2.  **Sensible Defaults**: Always provide defaults where possible to allow zero-config usage.
3.  **Rich Descriptions**: Use `Field(description=...)` for arguments and detailed descriptions for config params. This is the primary UI for the LLM and the developer.
4.  **Use Enums**: For discrete choices, use Python `Enum`s in arguments or `ParameterType.ENUM` in config to enforce correctness.

---

## 7. Future Extensions

- **CLI Integration**: A CLI command to list available tools and their required config options.
- **Declarative Specs**: A top-level YAML/JSON spec to wire up tools and config without writing Python instantiation code.
- **Auto-Validation**: Adding a flag to `ToolRegistry.create_tool` to enforce config validation automatically.
