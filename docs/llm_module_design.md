# LLM Module Design and Implementation

## 1. Overview

The `autobyteus.llm` module provides a unified, extensible interface for interacting with various Large Language Models (LLMs). It abstracts away the differences between providers (OpenAI, Anthropic, Mistral, etc.) and runtimes (Cloud APIs vs. Local Servers like Ollama/LM Studio), allowing the rest of the Autobyteus framework to treat all models uniformly.

## 2. Core Architecture

The architecture relies on a **Factory Pattern** combined with a **Registry** to manage model instantiation and discovery.

### 2.1 Class Hierarchy

- **`BaseLLM` (Abstract Base Class):**
  The foundation for all LLM implementations. It manages:
  - **Message History:** `add_user_message`, `add_assistant_message`.
  - **System Prompts:** Configuration and dynamic updates.
  - **Extensions:** Registry for plugins like token usage tracking.
  - **Hooks:** `before_invoke` and `after_invoke` lifecycle hooks.
  - **Abstract Methods:** Subclasses must implement `_send_user_message_to_llm` (unary) and `_stream_user_message_to_llm` (streaming).

- **`LLMModel`:**
  Represents the *metadata* of a model, not the active instance. It contains:
  - **Identifier:** A globally unique string (e.g., `gpt-4o`, `llama3:latest:ollama@localhost:11434`).
  - **Provider:** The organization that created the model (e.g., `OPENAI`).
  - **Runtime:** Where the model is hosted (e.g., `API`, `OLLAMA`).
  - **Factory Method:** `create_llm()` instantiates the concrete `BaseLLM` for this model.

- **`LLMFactory` (Singleton):**
  The central access point.
  - **Registry:** Maps unique identifiers to `LLMModel` instances.
  - **Discovery:** automatically discovers local models from runtimes like Ollama and registers them at startup.
  - **Creation:** `create_llm(identifier)` is the standard way to get a usable LLM object.

### 2.2 Provider vs. Runtime

A key architectural distinction is made between **Provider** and **Runtime**:

- **`LLMProvider`:** Who *made* the model?
  - Examples: `OPENAI`, `ANTHROPIC`, `MISTRAL`, `DEEPSEEK`.
- **`LLMRuntime`:** Where is the model *running*?
  - `API`: Cloud-hosted (e.g., accessing GPT-4 via OpenAI's API).
  - `OLLAMA`: Locally hosted via `ollama serve`.
  - `LMSTUDIO`: Locally hosted via LM Studio.
  - `AUTOBYTEUS`: Internal or custom serving layer.

This allows a model like `Llama 3` to exist as both an API model (via Groq or DeepInfra) and a local model (via Ollama), distinguished by their runtime.

## 3. Usage Flow

1.  **Initialization:**
    `LLMFactory.ensure_initialized()` is called. It:
    - Registers hardcoded API models (GPT-4, Claude 3.5, etc.).
    - Probes local runtimes (Ollama, LM Studio) to discover available models.

2.  **Instantiation:**
    The system requests a model by ID:
    ```python
    llm = LLMFactory.create_llm("gpt-4o")
    # or
    llm = LLMFactory.create_llm("llama3:latest:ollama@localhost:11434")
    ```

3.  **Interaction:**
    The agent interacts with the uniform `BaseLLM` interface:
    ```python
    await llm.send_user_message(user_message)
    # or
    async for chunk in llm.stream_user_message(user_message):
        process(chunk)
    ```

## 4. Extensibility

### 4.1 Adding a New Cloud Provider

1.  **Create concrete LLM class:** Subclass `BaseLLM` (e.g., `NewProviderLLM`) in `autobyteus/llm/api/`. Implement `_send...` and `_stream...` methods.
2.  **Update Enums:** Add the provider to `LLMProvider`.
3.  **Register Models:** Add `LLMModel` entries to `LLMFactory._initialize_registry`.

### 4.2 Extensions System

The `BaseLLM` supports extensions that hook into the request/response lifecycle.

- **`TokenUsageTrackingExtension`:** Automatically registered. Tracks input/output tokens and cost based on `LLMConfig`.
- **Custom Extensions:** Can be registered via `register_extension`. Useful for logging, rate limiting, or PII redaction.

## 5. Directory Structure

```text
autobyteus/llm/
├── api/                # Concrete BaseLLM implementations (OpenAI, Claude, etc.)
├── extensions/         # LLM extensions (Token usage, etc.)
├── providers/          # Discovery logic for runtimes (Ollama, LM Studio)
├── utils/              # Config, Message types, Pricing models
├── base_llm.py         # Abstract base class
├── llm_factory.py      # Singleton registry and factory
├── models.py           # LLMModel metadata definition
└── runtimes.py         # Runtime Enum definition
```

## 6. Configuration

`LLMConfig` controls model behavior:
- **`temperature`**: Sampling randomness.
- **`max_tokens`**: Output limit.
- **`system_message`**: Default system prompt.
- **`pricing_config`**: Cost per million tokens (input/output).

This config can be set globally per model in `LLMFactory` or overridden per instance during `create_llm`.
