# Extensible Tool Parsing Strategies

Date: 2025-11-18  
Status: Draft  
Authors: Autobyteus Agents Team

## Context & Goals

The Autobyteus agent currently identifies tool invocations through a `ProviderAwareToolUsageProcessor`, which delegates to a `ProviderAwareToolUsageParser`. This parser knows how to interpret provider-specific tool formats (e.g., OpenAI function calls) but does **not** natively understand filesystem skill modules, so the processor manually invokes `FilesystemModuleUsageParser`. That conditional branch is brittle and makes “module calls” feel special even though they eventually flow through the same execution pipeline as any other tool.

We want:

1. **Uniform handling** — every tool invocation, including filesystem modules, enters the queue via the same parsing pathway.
2. **Extensibility** — adding a new tool syntax or provider quirk should be as simple as dropping in a new parsing strategy without touching core processors.
3. **Skill-driven flexibility** — skills should be able to register custom parsers (e.g., bespoke delimiters) when they load.
4. **Gradual migration** — reuse existing parsing logic by wrapping it, not rewriting it from scratch.

## High-Level Design

We introduce a lightweight **strategy registry** inside `ProviderAwareToolUsageParser`. Each strategy encapsulates the logic for a single syntax/provider. The parser iterates over registered strategies, lets each extract `ToolInvocation` objects, and aggregates their results. The processor no longer needs to special-case filesystem modules; it simply calls `parser.parse()` and receives every invocation.

```
LLM Response
    │
    ▼
ProviderAwareToolUsageProcessor
    │
    ▼
ProviderAwareToolUsageParser
    │
    ├─ Strategy: OpenAI JSON/function_call
    ├─ Strategy: Anthropic tool_use XML
    └─ Strategy: Filesystem [RUN_MODULE] … [/RUN_MODULE]
         (plus any future skill-registered strategies)
    ▼
List[ToolInvocation] (uniform objects)
```

## Strategy Interface

```python
class ToolParseStrategy(ABC):
    @abstractmethod
    def supports(self, response: CompleteResponse, context: AgentContext) -> bool:
        """Return True if this strategy should inspect the response."""

    @abstractmethod
    def parse(self, response: CompleteResponse, context: AgentContext) -> List[ToolInvocation]:
        """Return tool invocations; may raise ToolUsageParseException."""
```

Key notes:

- `supports()` lets strategies skip work quickly (e.g., check provider name, look for sentinel tokens, etc.).
- Strategies can inspect both the raw text (`response.content`) and structured metadata (e.g., `response.parsed`, provider IDs in `context`).
- Strategies must return new `ToolInvocation` objects; the processor will assign unique IDs and enqueue them like any other tool call.

## Parser Registry Behavior

```python
class ProviderAwareToolUsageParser(BaseToolUsageParser):
    def __init__(self, strategies: Optional[List[ToolParseStrategy]] = None):
        self._strategies = strategies or [
            OpenAIFunctionCallStrategy(),
            AnthropicToolUseStrategy(),
            FilesystemModuleStrategy(),
        ]

    def register_strategy(self, strategy: ToolParseStrategy, *, prepend: bool = False):
        if prepend:
            self._strategies.insert(0, strategy)
        else:
            self._strategies.append(strategy)

    def parse(self, response, context) -> List[ToolInvocation]:
        invocations: List[ToolInvocation] = []
        for strategy in self._strategies:
            if not strategy.supports(response, context):
                continue
            invocations.extend(strategy.parse(response, context))
        return invocations
```

- Strategies are evaluated in order; this allows specialized parsers to “win” before more generic ones.
- Registration is cheap, so skills can push their strategies at runtime (e.g., via `SkillInjectorProcessor` hook).

## Adapting Existing Parsers

1. **OpenAI Function Calls** — wrap current JSON parsing logic inside `OpenAIFunctionCallStrategy`.
2. **Anthropic Tool Use** — move the Anthropic XML parsing function into `AnthropicToolUseStrategy`.
3. **Filesystem Modules** — transplant `FilesystemModuleUsageParser`’s regex/JSON logic into `FilesystemModuleStrategy`. The standalone parser file can either house the strategy class or export helper functions.
4. **Other Providers** — follow the same “wrap existing logic” approach. No behavioral changes expected.

This “adapter” technique avoids dramatic refactoring. We simply relocate code into strategy classes and register them.

## Skill-Registered Strategies

Skills may describe custom parsing needs in their metadata (`skill.md`). Once the skill loads:

1. Resolve its metadata into a `ToolParseStrategy` implementation (e.g., `SkillDeclaredStrategy`).
2. Register it with the parser: `context.config.tool_parser.register_strategy(skill_strategy, prepend=True)` if it should override defaults.
3. Deregister on skill unload if necessary.

Example strategy skeleton:

```python
class SkillDeclaredStrategy(ToolParseStrategy):
    def __init__(self, trigger_name: str, pattern: str):
        self.trigger_name = trigger_name
        self.pattern = re.compile(pattern, re.DOTALL | re.IGNORECASE)

    def supports(self, response, context):
        text = response.content or ""
        return self.pattern.search(text) is not None

    def parse(self, response, context):
        invocations = []
        for match in self.pattern.finditer(response.content or ""):
            payload = json.loads(match.group(1))
            invocations.append(ToolInvocation(name=self.trigger_name, arguments=payload.get("args", {})))
        return invocations
```

## Processor Interaction

`ProviderAwareToolUsageProcessor.process_response()` stays essentially unchanged except that the explicit call to `FilesystemModuleUsageParser` disappears:

```python
tool_invocations = self._parser.parse(response, context)
if not tool_invocations:
    return False
self._assign_unique_ids(tool_invocations, context)
await self._enqueue(tool_invocations, context)
```

All invocations—provider-native or module-based—arrive through `_parser`.

## Migration Steps

1. Create `ToolParseStrategy` base and registry methods.
2. Wrap existing provider parsers into strategy classes; register them.
3. Move filesystem module logic into a strategy and register it by default (optionally only when `skill_file_paths` is non-empty).
4. Remove `use_module_protocol` field and any processor-level conditionals (already done).
5. Optionally expose hooks so skills can add/remove strategies dynamically.

## Risks & Mitigations

- **Performance**: multiple strategies might scan the same text. Mitigate with cheap `supports()` checks and ordered evaluation.
- **Error Propagation**: strategy exceptions bubble up through the parser, preserving current behavior (processor already handles `ToolUsageParseException`).
- **Ordering Conflicts**: ensure strategies that might compete for the same syntax are ordered intentionally or inspect context carefully.

## Future Extensions

- Strategy metadata could include priority numbers instead of simple ordering.
- Strategies might declare dependencies (e.g., “run me only after provider-level parsing to inspect untouched segments”).
- Provide a YAML/JSON descriptor that auto-generates `SkillDeclaredStrategy` instances for simple patterns, avoiding custom Python code per skill.

With this structure documented, we can proceed to implementation knowing exactly how modules become “just another tool call” via pluggable parsing strategies.
