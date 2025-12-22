# Local Engine Deployment Research (Phase 2)

## 1. Purpose & Scope
Phase 2 explores how Autobyteus can ship and manage the llama.cpp and MLX engines directly, instead of relying on Ollama or LM Studio. This document summarizes deployment options, binary availability, and operational considerations (model lifecycle, platform coverage, packaging size).

## 2. llama.cpp Deployment Landscape
### 2.1 Official Distribution Channels
- **Source & package builds** — upstream docs highlight cloning `ggml-org/llama.cpp`, compiling locally, and launching the OpenAI-compatible server (`llama-server -hf …`).citeturn1search5
- **Package managers** — the maintained Homebrew formula provides bottles for macOS (Intel/Apple Silicon) and Linux, simplifying developer onboarding.citeturn1search2
- **Docker** — official GHCR images (`full`, `light`, `server`, CUDA/ROCm variants) expose the server binary directly; we can run `ghcr.io/ggerganov/llama.cpp:server` with volume mount + port mapping for turnkey deployments.citeturn10search1

### 2.2 Pre-built Binaries
- Official builds include distinct archives for macOS arm64, Windows AVX/AVX2, CUDA, ROCm, and SYCL targets, so we can bundle only the slices required per platform.citeturn6search2
- Community-maintained wheels such as the CUDA/Metal variants of `llama-cpp-python` let us deliver Python-based runtimes without compiling from source.citeturn2search6
- Docker images cover CPU, CUDA, and ROCm builds, giving us a reproducible packaging baseline if we prefer container distribution.citeturn10search1

### 2.3 Loading & Unloading Models
- The OpenAI-compatible server bundled with `llama_cpp_python` lists `/v1/models`, supports aliases, and automatically loads/unloads models defined in a config file as requests arrive.citeturn3search0
- Native `llama-server` is single-model per process; orchestration tools like `llama-swap` and FlexLLama manage fleets to emulate hot-swapping without restarts.citeturn3search1turn1reddit13
- GGUF checkpoints can be streamed directly from Hugging Face via `--hf-repo` and cached under `LLAMA_CACHE`, easing initial provisioning and future cache hits.citeturn5search0

### 2.4 Operational Gaps
- Operators observe that first-request latency against newly started containers can be much higher than steady-state, so warm-up probes matter for production readiness.citeturn6search0
- Quantised 7B models still require roughly 4 GB RAM, so managed deployments should enforce resource checks before loading larger checkpoints.citeturn9search0

## 3. MLX Deployment Landscape
### 3.1 Official Distribution Channels
- `mlx-lm` installs via pip/conda and includes `mlx_lm.server`, an OpenAI-compatible HTTP server configurable with host, port, chat template, draft model, and speculative decoding flags.citeturn7search2turn8search2
- Alternative servers (`mlx-llm-server`, `mlx-openai-server`) expose similar APIs and are published as Python packages, reinforcing that MLX distribution today assumes a managed Python runtime rather than standalone binaries.citeturn7search0turn7search11
- Net takeaway: bundling MLX means shipping a curated Python environment (e.g., Miniforge + wheels) or wrapping these packages inside a macOS app; there is no official monolithic binary yet.citeturn7search0

### 3.2 Model Preparation
- MLX Community repos on Hugging Face supply ready-to-run checkpoints; `mlx_lm.convert` handles conversion/quantisation so we can pre-bake or cache `.mlx` artifacts.citeturn14view0
- The server CLI exposes knobs like `--draft-model`, `--chat-template`, and `--max-kv-size`, letting us tune throughput without modifying source.citeturn8search2

### 3.3 Loading & Unloading Models
- `mlx_lm.server` loads the model named via `--model` (plus optional adapters) during startup; documentation implies switching models requires restarting with new flags. (Inference based on CLI usage.)citeturn8search2
- Third-party wrappers such as `mlx-llm-server` and `mlx-openai-server` add features like queue sizing and concurrency caps but still dedicate each process to a single model path.citeturn7search0turn7search11

## 4. Deployment Strategies for Autobyteus
### 4.1 Binary Packaging Options
| Option | Description | Pros | Cons |
| --- | --- | --- | --- |
| **Bundle curated binaries** | Ship llama.cpp release zips/wheels plus a prepared MLX Python env inside Autobyteus Server images | Predictable, offline-friendly startup | Large image sizes (≥373 MB for CUDA runtime, >2 GB for CUDA Docker layers), multi-arch maintenance overhead |
| **On-demand download** | Detect platform → fetch the matching release asset or wheel at install/start | Smaller initial footprint, easier upgrades | Needs network access and checksum enforcement; must handle failed downloads gracefully |
| **Self-build at install time** | Run scripted CMake builds for llama.cpp and assemble MLX wheels locally | Maximum hardware optimisation and feature flags | Slow first-run experience; requires compilers/SDKs on target machines |

### 4.2 Recommended Approach
1. **Phase 2 pilot**: default to on-demand download with cached artifact manifests. Provide overrides to supply pre-bundled assets for offline deployments.
2. **Platform coverage**:
   - Linux x86_64 CPU/GPU: catalogue AVX2/CUDA release assets alongside GHCR Docker images (`server`, `server-cuda`) for container-first installs.citeturn6search2turn10search1
   - macOS/Apple Silicon: lean on `pip install mlx-lm`/`mlx-llm-server` with a managed Miniforge base or offer a prebuilt Apple silicon archive.citeturn7search2turn7search0
   - Windows: reference upstream release zips by architecture; keep optional curated mirrors for air-gapped environments.citeturn6search2
3. **Artifact manifest**: maintain JSON mapping `{platform, accel, version} → {url, checksum, size}` to allow deterministic downloads and footprint forecasts.

### 4.3 Model Lifecycle Controls
- **Load**: support three modes — (a) auto-download via `-hf`/`mlx-community` repo IDs, (b) local path, (c) curated bundle. Provide CLI helpers to pre-pull into cache directories.
- **Unload**: expose admin API only where engine supports it reliably (e.g., llama.cpp via multi-model config). For MLX, document the restart requirement or run multiple workers to simulate unload by process rotation.citeturn3search0turn8search2
- **Swap**: optionally integrate with wrappers (`llama-swap`, FlexLLama) to deliver dynamic switching for operators needing multi-model concurrency without manual restarts.citeturn3search1turn1reddit13

### 4.4 Operational Safeguards
- Enforce RAM/disk checks before loading large GGUFs or MLX checkpoints; warn when quantised models (e.g., 7B ≈4 GB) would exceed available memory headroom.citeturn9search0
- Surface cache locations (`LLAMA_CACHE`, MLX model directories) in server diagnostics so operators can manage storage growth.citeturn5search0turn14view0
- Provide version pinning and rollback: keep previous binaries/models alongside current ones, tracked in the manifest.

## 5. Next Steps
1. Prototype installer scripts for each platform that implement the on-demand download workflow and record checksums.
2. Define Autobyteus Server orchestration hooks to start/stop engines and guard against unsupported unload operations.
3. Run size/time benchmarks for first-run download vs. bundled assets to decide default behaviour per deployment profile.
4. Document operator playbooks (upgrade, model cache purge, troubleshooting memory errors) before GA rollout.
