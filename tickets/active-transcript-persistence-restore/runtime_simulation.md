# Runtime Simulation (Restore + Continue)

This is a **production-level, code-aligned** call stack simulation based on the current Autobyteus runtime and the proposed restore design. It uses real modules and functions and highlights where the new design hooks in.

## 1) Restore Flow (proposed, cache-first with fallback rebuild)

```
agent/factory/agent_factory.py:restore_agent(agent_id, config, memory_dir=None)
├── agent/factory/agent_factory.py:_create_runtime_with_id(agent_id, config)
│   ├── agent/context/agent_runtime_state.py:__init__(agent_id, workspace, custom_data)
│   ├── memory/store/file_store.py:__init__(base_dir, agent_id)  # memory/agents/<agent_id>
│   ├── memory/store/working_context_snapshot_store.py:__init__(base_dir, agent_id)
│   ├── memory/memory_manager.py:__init__(store, turn_tracker=None, compaction_policy=None, compactor=None, retriever=None, working_context_snapshot=None, working_context_snapshot_store=None)
│   └── agent/context/agent_context.py:__init__(agent_id, config, state)
│
├── agent/agent.py:start()  # starts worker thread
│   └── agent/runtime/agent_worker.py:async_run()
│       ├── agent/runtime/agent_worker.py:_runtime_init()
│       │   └── agent/events/agent_input_event_queue_manager.py:__init__(queue_size)
│       ├── agent/runtime/agent_worker.py:_initialize()
│       │   ├── agent/events/agent_input_event_queue_manager.py:enqueue_internal_system_event(BootstrapStartedEvent)
│       │   └── agent/events/worker_event_dispatcher.py:dispatch(event, context)
│       │       └── agent/handlers/bootstrap_event_handler.py:handle(event, context)
│       │           ├── agent/bootstrap_steps/workspace_context_initialization_step.py:execute(context)
│       │           ├── agent/bootstrap_steps/mcp_server_prewarming_step.py:execute(context)
│       │           ├── agent/bootstrap_steps/system_prompt_processing_step.py:execute(context)
│       │           │   └── agent/system_prompt_processor/*:process(system_prompt, ...)
│       │           └── agent/bootstrap_steps/working_context_snapshot_restore_step.py:execute(context)  # NEW (restore-only, guarded)
│       │               ├── agent/context/agent_runtime_state.py:restore_options  # set by restore call
│       │               └── memory/restore/working_context_snapshot_bootstrapper.py:bootstrap(memory_manager, system_prompt, options)
│       │                   ├── memory/store/working_context_snapshot_store.py:exists(agent_id)
│       │                   ├── memory/store/working_context_snapshot_store.py:read(agent_id)
│       │                   ├── memory/working_context_snapshot_serializer.py:validate(payload)
│       │                   ├── memory/working_context_snapshot_serializer.py:deserialize(payload)
│       │                   └── memory/memory_manager.py:reset_working_context_snapshot(snapshot_messages)
│       │
│       │                   # Fallback path if cache is missing/invalid
│       │                   ├── memory/retrieval/retriever.py:retrieve(max_episodic, max_semantic)
│       │                   ├── memory/memory_manager.py:get_raw_tail(tail_turns, exclude_turn_id=None)
│       │                   ├── memory/compaction_snapshot_builder.py:build(system_prompt, bundle, raw_tail)
│       │                   └── memory/memory_manager.py:reset_working_context_snapshot(snapshot_messages)
```

## 2) Normal Turn After Restore (real code path)

```
agent/agent.py:post_user_message(agent_input_user_message)
└── agent/runtime/agent_runtime.py:submit_event(event)
    └── agent/runtime/agent_worker.py:async_run()
        └── agent/events/worker_event_dispatcher.py:dispatch(event, context)
            └── agent/handlers/user_input_message_event_handler.py:handle(event, context)
                ├── agent/input_processor/memory_ingest_input_processor.py:process(message, context, triggering_event)
                │   └── memory/memory_manager.py:ingest_user_message(llm_user_message, turn_id, source_event)
                │
                ├── agent/message/multimodal_message_builder.py:build_llm_user_message(message)
                └── agent/events/agent_input_event_queue_manager.py:enqueue_internal_system_event(event)
                    └── agent/events/worker_event_dispatcher.py:dispatch(event, context)
                        └── agent/handlers/llm_user_message_ready_event_handler.py:handle(event, context)
                            ├── agent/llm_request_assembler.py:prepare_request(processed_user_input, current_turn_id, system_prompt)
                            │   ├── memory/memory_manager.py:get_working_context_messages()
                            │   ├── llm/prompt_renderers/openai_chat_renderer.py:render(messages)
                            │   └── memory/memory_manager.py:working_context_snapshot.append_message(message)
                            │
                            ├── llm/base_llm.py:stream_messages(messages, rendered_payload, **kwargs)
                            │   └── llm/api/*:stream_messages(messages, rendered_payload, **kwargs)  # provider-specific
                            │
                            ├── agent/streaming/*:StreamingResponseHandler.handle(chunk_response)
                            │   └── agent/handlers/llm_user_message_ready_event_handler.py:emit_segment_event(event)
                            │
                            ├── memory/memory_manager.py:ingest_tool_intent(tool_invocation, turn_id)   # if tool calls
                            │   └── agent/events/agent_input_event_queue_manager.py:enqueue_tool_invocation_request(event)
                            │
                            └── memory/memory_manager.py:ingest_assistant_response(response, turn_id, source_event)
                                └── memory/memory_manager.py:request_compaction()  # only sets flag
```

## 3) Tool Execution Loop (real code path)

```
agent/events/worker_event_dispatcher.py:dispatch(event, context)
└── agent/handlers/tool_invocation_request_event_handler.py:handle(event, context)
    ├── tools/*:execute(context, **kwargs)
    └── agent/events/agent_input_event_queue_manager.py:enqueue_tool_result(event)
        └── agent/events/worker_event_dispatcher.py:dispatch(event, context)
            └── agent/handlers/tool_result_event_handler.py:handle(event, context)
                ├── agent/tool_execution_result_processor/memory_ingest_tool_result_processor.py:process(event, context)
                │   └── memory/memory_manager.py:ingest_tool_result(event, turn_id)
                │
                └── agent/handlers/tool_result_event_handler.py:_dispatch_results_to_input_pipeline(processed_events, context)
                    └── agent/events/agent_input_event_queue_manager.py:enqueue_user_message(event)
                        └── agent/handlers/user_input_message_event_handler.py:handle(event, context)
                            └── agent/input_processor/memory_ingest_input_processor.py:process(message, context, triggering_event)
                                └── (skipped for SenderType.TOOL to avoid duplicate tool results)
```

## 4) Compaction (real timing)

Compaction is **not executed immediately** when usage exceeds budget. It is **requested** in\n`LLMUserMessageReadyEventHandler` after the response, and **executed on the next LLM call** in\n`LLMRequestAssembler.prepare_request()` when `compaction_required` is set.

```
agent/handlers/llm_user_message_ready_event_handler.py:handle(event, context)
└── memory/memory_manager.py:request_compaction()  # sets flag only

# Next LLM call:
agent/llm_request_assembler.py:prepare_request(processed_user_input, current_turn_id, system_prompt)
└── memory/compaction/compactor.py:compact(turn_ids)
    ├── memory/compaction/summarizer.py:summarize(traces)
    ├── memory/store/file_store.py:add(items)          # episodic + semantic
    ├── memory/store/file_store.py:prune_raw_traces(keep_turn_ids, archive=True)
    ├── memory/compaction_snapshot_builder.py:build(system_prompt, bundle, raw_tail)
    └── memory/memory_manager.py:reset_working_context_snapshot(snapshot_messages)
        └── memory/memory_manager.py:persist_working_context_snapshot()  # new hook
```

---

# Analysis (Design Fit / Gaps)

## Responsibility Scoping
- Restore orchestration is isolated in `AgentRestoreService` (new).
- Serialization/IO is separated (`Serializer` vs `WorkingContextSnapshotStore`).
- Restore strategy lives in `WorkingContextSnapshotBootstrapper` (new).
- Runtime flow stays unchanged except for persistence hooks.

## Memory Access vs Execution Phase
- Restore reads memory **before** runtime handles user input.
- Runtime flow writes memory during input and tool result processing.
- Compaction runs **on the next LLM call** after a request flag is set.

## Execution Order Coherence
- System prompt is prepared before working context snapshot reconstruction.
- Working context snapshot is ready before any LLM call after restore.
- Persistence hooks run at stable boundaries (after reset, after assistant response).

## Potential Gaps / Risks
- **Cache staleness** between tool results and assistant response (working context snapshot changes but not persisted). Mitigation: persist on tool call/result or accept fallback rebuild on restore.
- **System prompt mismatch**: working context snapshot cache assumes the current system prompt matches what produced it.
- **Tool payload serialization**: large/non-JSON tool results need truncation or references (`tool_result_ref`).
- **Agent ID reuse**: restore must create runtime with existing `agent_id`; `create_agent()` currently generates a new one.

## Conclusion
The design aligns with the real execution path. The main gaps are cache freshness around tool results and system prompt hash validation. Both are fixable with small, well-scoped hooks.
