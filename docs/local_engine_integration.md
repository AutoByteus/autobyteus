# Local Engine Integration Design

## 1. Purpose
Document how to extend the Autobyteus framework and Autobyteus Server so they can run large language models directly on user-managed llama.cpp and MLX engines, removing the hard dependency on third-party launchers such as Ollama or LM Studio.

## 2. Background
- **Current behaviour**: Autobyteus discovers local runtimes through `OllamaModelProvider` and `LMStudioModelProvider`, both of which wrap OpenAI-compatible HTTP endpoints exposed by those desktop applications.
- **Motivation**: Ollama and LM Studio internally delegate work to the [llama.cpp](https://github.com/ggerganov/llama.cpp) server and Apple’s [MLX LLM tooling](https://github.com/ml-explore/mlx-examples/tree/main/llms). Supporting these engines directly provides more control, removes an extra dependency, and broadens platform coverage (e.g., headless servers).
- **Downstream dependency**: `autobyteus-server` consumes the Autobyteus framework as a library. Any new runtime or provider capability must work both inside the core package and within the server deployment flows.

## 3. Goals & Non-Goals
### Goals
- Add first-class provider/runtime support for:
  - llama.cpp HTTP server (`./server`) and optional WebSocket/GRPC endpoints.
  - MLX LLM server (`python -m mlx_lm.server serve`).
- Keep the provider discovery pattern consistent with existing Ollama/LM Studio integrations.
- Allow Autobyteus Server to use the same discovery logic, preserving a single source of truth.
- Provide tooling and documentation so ops teams can decide whether engines are bundled or downloaded on-demand.

### Non-Goals
- Ship a precompiled binary for every llama.cpp target architecture in this iteration.
- Implement GPU driver installation or low-level model quantisation flows.
- Replace the existing Ollama/LM Studio integrations (they remain supported).

## 4. Architectural Overview
### 4.1 High-Level Flow
1. **Configuration**: User or deployment configuration supplies one or more host URLs for each engine type.
2. **Discovery**: During `LLMFactory.ensure_initialized`, new provider classes call the engine’s `/v1/models` endpoint (OpenAI-compatible) to enumerate available models.
3. **Registration**: Each discovered model is wrapped in an `LLMModel` instance with runtime metadata and registered in the shared registry.
4. **Invocation**: Autobyteus clients select models the same way they do today; the provider-specific LLM class handles transport details (REST streaming, SSE, WebSocket).

### 4.2 Components to Add
| Component | Location | Responsibility |
|-----------|----------|----------------|
| `LLMRuntime.LLAMA_CPP` & `LLMRuntime.MLX` | `autobyteus/llm/runtimes.py` | Identify the serving engine at runtime. |
| `LLMProvider.LLAMA_CPP` & `LLMProvider.MLX` | `autobyteus/llm/providers.py` | Expose selectable providers in UI/CLI layers. |
| `LlamaCppModelProvider` | `autobyteus/llm/llama_cpp_provider.py` | Host discovery, model registration, health checks. |
| `MLXModelProvider` | `autobyteus/llm/mlx_provider.py` | Same as above for MLX. |
| `LlamaCppLLM` & `MLXLLM` | `autobyteus/llm/api` | API client implementation using shared OpenAI-compatible transport helpers. |
| Shared OpenAI transport adapter | `autobyteus/llm/api/shared_openai_runtime.py` (new) | Consolidate duplicated code between LM Studio, llama.cpp, MLX. |
| Server orchestration hooks | `autobyteus-server/services/llm_runtime_bootstrap.py` (new) | Optional helper to launch engines or prompt users during server start-up. |

## 5. Provider Design Details
### 5.1 llama.cpp Provider
- **Discovery endpoints**: `GET /v1/models`, `POST /v1/chat/completions`, `POST /v1/completions`, `GET /health` (or `POST /health` depending on build).
- **Configuration**:
  - `LLAMACPP_HOSTS`: comma-separated list of base URLs (default `http://localhost:8000`). Supports HTTP(S).
  - `LLAMACPP_HEALTHCHECK`: toggle to skip blocking health tests in high-availability environments.
- **Registration**:
  - Models are tagged with `runtime=LLMRuntime.LLAMA_CPP`.
  - `default_config` exposes engine-relevant defaults (context window, GPU layers, quantisation type if returned by the model listing).
- **Error handling**: Wrap connection failures with actionable logging, mirroring the Ollama provider.
- **Streaming**: Use Server-Sent Events from `/v1/chat/completions` when the engine responds with `event: completion.chunk`.

### 5.2 MLX Provider
- **Discovery options**:
  - Preferred: call the running server’s `GET /v1/models`.
  - Fallback: execute `python -m mlx_lm.server list --json` (captured in a subprocess) when no HTTP endpoint is available yet.
- **Configuration**:
  - `MLX_HOSTS` (default `http://localhost:8000`).
  - `MLX_LAUNCH_COMMAND`: optional command used by Autobyteus Server to bootstrap the engine if not already running.
- **Model metadata**: the MLX server returns context length, quantisation, and template information; map these into `LLMConfig`.
- **Transport**: identical to llama.cpp (OpenAI-compatible JSON).

## 6. Autobyteus Server Integration
- Share provider discovery logic by importing `LLMFactory` exactly as the framework does. No forks in code paths.
- On server start-up:
  1. Load server-side configuration (`config.toml` or environment).
  2. Optionally invoke an engine bootstrapper (see §7) if hosts are marked as `managed`.
  3. Call `LLMFactory.ensure_initialized()`; new providers register themselves transparently.
- Provide admin APIs or CLI commands in Autobyteus Server to:
  - List available local engines/models.
  - Trigger reload (`LLMFactory.reinitialize()`).
  - Surface health status for each host (connection status, last latency, error reason).

## 7. Engine Distribution Strategy
### Option A — Bundle Engines with Autobyteus Server
**Pros**
- End-to-end experience out of the box.
- Controlled binary versions.

**Cons**
- Large binaries per target (CPU-only, CUDA, Metal, ROCm each different).
- Frequent upstream updates; maintaining patched builds is costly.
- Potential licensing friction distributing vendor-specific blobs.

### Option B — Auto-Download on First Use
**Pros**
- Keeps server footprint small.
- Allows per-platform optimisation (download CUDA build on Linux GPU, Metal on macOS).
- Provides opportunity to auto-download models as part of onboarding flows.

**Cons**
- Requires network access and extra installation logic (permissions, antivirus false positives).
- Need to manage caching, upgrades, and failed installs gracefully.

### Recommendation
1. **Default** to Option B: detect platform, fetch published release assets for llama.cpp (official releases provide prebuilt binaries) or install via `pip install mlx-lm` on macOS. Cache under a writable directory controlled by Autobyteus Server.
2. **Provide opt-out**: configuration flag `LLM_HOST_MANAGEMENT=external` to skip downloads and rely entirely on user-provided hosts.
3. **Support pre-bundled builds**: document how ops teams can bake binaries into Docker images or deployment bundles; detection logic should short-circuit if a binary path is already configured.

## 8. Engine Lifecycle Management
- **Bootstrapper**: `autobyteus-server` acquires a `ManagedLocalEngine` abstraction that can:
  - Check whether the engine process is already running (PID file or TCP probe).
  - Launch it with configured command (e.g., `./server -m ...` or `python -m mlx_lm.server serve ...`).
  - Monitor stdout/stderr for readiness, streaming diagnostics into server logs.
- **Model acquisition**:
  - Provide helper scripts (`scripts/llama_cpp_pull_model.py`, `scripts/mlx_pull_model.py`) to download GGUF or `mlx` checkpoints using URLs or Hugging Face IDs.
  - Allow Autobyteus Server to call these scripts pre-flight.
- **Updates**:
  - Implement semantic version tracking in a simple JSON manifest (`~/.autobyteus/engines/manifest.json`).
  - Expose CLI tooling (`autobyteus-server engines upgrade`) to pull newer binaries/models with rollback.

## 9. Configuration Model
- Extend `.env.example` and docs with:
  ```
  LLAMACPP_HOSTS=http://localhost:8000
  LLAMACPP_MANAGED=true
  LLAMACPP_BINARY_PATH=./bin/llama-server
  LLAMACPP_DEFAULT_MODEL=meta-llama/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf

  MLX_HOSTS=http://localhost:8001
  MLX_MANAGED=true
  MLX_PYTHON_BIN=/opt/miniconda/envs/autobyteus/bin/python
  MLX_DEFAULT_MODEL=mlx-community/Mistral-7B-Instruct-v0.2
  ```
- Document precedence: explicit host URLs override managed launchers; if both `*_MANAGED` and `*_HOSTS` are set, attempt managed start first, then fall back to existing hosts.

## 10. Security & Compliance
- Respect network isolation: when bundling or downloading, ensure engines run only on loopback interfaces by default; expose `ALLOW_REMOTE` flag for trusted deployments.
- Provide API key handling for `mlx_lm.server` (supports optional OpenAI-style keys); store them in the same secrets manager as other providers.
- Log redaction: engine logs may contain prompts; redact before writing to shared server logs.

## 11. Testing Strategy
- **Unit tests**: mock HTTP responses for `/v1/models` and `/v1/chat/completions` across success, timeout, and malformed payloads.
- **Integration tests**: use docker-compose or GitHub Actions to run llama.cpp server with a small model (TinyLlama) and verify discovery + inference.
- **Server tests**: in autobyteus-server, add e2e tests that launch managed engines, perform prompt calls, and tear down cleanly.

## 12. Rollout Plan
1. Implement shared transport adapter and new providers in the Autobyteus framework.
2. Update documentation and configuration templates.
3. Release Autobyteus library with new providers (feature flag disabled by default).
4. Update Autobyteus Server to:
   - Consume the new library version.
   - Add optional managed engine launcher.
   - Document deployment choices (bundle vs auto-download vs external).
5. Run pilot deployment with internal users to validate performance and UX.
6. Announce availability and iterate based on feedback.

## 13. Open Questions
- Should we maintain a curated list of recommended quantised GGUF checkpoints for quick starts?
- How do we expose hardware-specific flags (CUDA vs Metal vs CPU) through configuration without overwhelming users?
- Do we need to support remote, multi-user inference clusters (e.g., llama.cpp running in Kubernetes) in this release, or is that deferred?
