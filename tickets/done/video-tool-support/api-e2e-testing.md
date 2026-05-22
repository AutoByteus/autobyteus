# API / E2E / Executable Validation

## Status

- Current Status: `Pass`
- Scope: Video-generation tool support in `autobyteus`
- Validation Date: 2026-05-22

## Environment

- Test runner: `uv run --extra dev python -m pytest`
- Local setup note: this dedicated worktree required a local ignored `.env.test` copied from `.env.example` because `tests/conftest.py` fails collection without that file.
- Live video generation: Rerun on 2026-05-22 after the Docker LLM server was restarted with the released video endpoint. The first server instance on `https://127.0.0.1:51739` reached `/generate-video` but returned a backend browser-state 500 because a Gemini overlay intercepted the prompt textbox click. The second server instance on `https://127.0.0.1:51740` passed through the real `GenerateVideoTool` path and produced a saved MP4.

## Commands Run

| Command | Result |
| --- | --- |
| `uv run --extra dev python -m pytest tests/unit_tests/clients/test_autobyteus_client.py tests/unit_tests/multimedia/video tests/unit_tests/tools/multimedia/test_video_tools.py -q` | `27 passed` |
| `uv run --extra dev python -m pytest tests/unit_tests/tools/registry/test_tool_registry.py -q` | `16 passed` |
| `uv run --extra dev python -m pytest tests/unit_tests/multimedia/image tests/unit_tests/multimedia/audio/api/test_gemini_audio_client.py -q` | `9 passed` |
| `uv run --extra dev python -m pytest tests/unit_tests/clients/test_autobyteus_client.py tests/unit_tests/multimedia/video tests/unit_tests/tools/multimedia/test_video_tools.py tests/unit_tests/tools/registry/test_tool_registry.py tests/unit_tests/multimedia/image tests/unit_tests/multimedia/audio/api/test_gemini_audio_client.py -q` | `52 passed` |
| `uv run --extra dev python -m compileall -q autobyteus/multimedia/video autobyteus/tools/multimedia/video_tools.py autobyteus/clients/autobyteus_client.py` | Passed |
| Live `GenerateVideoTool` script with `AUTOBYTEUS_LLM_SERVER_HOSTS=https://127.0.0.1:51740`, `DEFAULT_VIDEO_GENERATION_MODEL=gemini-omni-app-rpa`, and API key from the RPA server `.env.test` | Passed; discovered `gemini-omni-app-rpa@127.0.0.1:51740`, exposed expected schema, generated and downloaded `/tmp/autobyteus-video-tool-live-51740/videos/live_tool_endpoint_smoke.mp4` in `82.1s` |
| `ffprobe -v error -show_entries format=duration,size -show_streams -of json /tmp/autobyteus-video-tool-live-51740/videos/live_tool_endpoint_smoke.mp4` | Passed; MP4 contains H.264 1280x720 video, AAC audio, 10.0s duration, 1,567,395 bytes |

## Acceptance Criteria Closure

| AC ID | Requirement(s) | Scenario ID | Evidence | Result |
| --- | --- | --- | --- | --- |
| AC-001 | R-001, R-009 | AV-001 | `tests/unit_tests/tools/multimedia/test_video_tools.py::test_existing_multimedia_tool_exports_remain_available` and import coverage in combined suite. | Passed |
| AC-002 | R-001 | AV-002 | `test_generate_video_tool_is_registered` verifies metaclass/registry definition. | Passed |
| AC-003 | R-002, R-003, R-004 | AV-003 | `test_generate_video_tool_schema_omits_generation_config_for_empty_model_schema`. | Passed |
| AC-004 | R-004 | AV-004 | `test_generate_video_tool_schema_includes_generation_config_for_parameterized_model`. | Passed |
| AC-005 | R-002, R-005, R-008 | AV-005 | `test_generate_video_tool_execute_splits_inputs_and_saves_output`. | Passed |
| AC-006 | R-008 | AV-006 | `test_generate_video_tool_raises_when_no_video_urls`. | Passed |
| AC-007 | R-006 | AV-007 | `test_get_available_video_models_uses_video_endpoint`, `test_generate_video_normalizes_media_sources`, `test_cleanup_video_session_uses_video_cleanup_endpoint`. | Passed |
| AC-008 | R-007 | AV-008 | `tests/unit_tests/multimedia/video/test_autobyteus_video_provider.py::test_discover_and_register_video_models`. | Passed |
| AC-009 | R-005, R-006 | AV-009 | `tests/unit_tests/multimedia/video/api/test_autobyteus_video_client.py`. | Passed |
| AC-010 | R-009 | AV-010 | `tests/unit_tests/tools/registry/test_tool_registry.py`, `tests/unit_tests/multimedia/image`, `tests/unit_tests/multimedia/audio/api/test_gemini_audio_client.py`. | Passed |
| AC-011 | R-003, R-007 | AV-011 | `tests/unit_tests/multimedia/video/test_video_client_factory.py` covers default registration, single unqualified match, ambiguity error, and client creation. | Passed |

## Spine Coverage Closure

| Spine ID | Covered By | Result |
| --- | --- | --- |
| DS-001 `GenerateVideoTool -> local saved file` | Tool schema/execution/error tests. | Passed |
| DS-002 `VideoClientFactory/provider discovery` | Video factory/provider/model tests. | Passed |
| DS-003 `AutobyteusClient video HTTP boundary` | HTTP payload/path tests and adapter tests. | Passed |
| Live `GenerateVideoTool -> Docker LLM server -> /generate-video -> downloaded MP4` | Real Docker endpoint run on `https://127.0.0.1:51740`; saved MP4 verified with `file` and `ffprobe`. | Passed |

## Feasibility / Waiver Record

- Live RPA video generation was executed during the Stage 10 validation recheck on `https://127.0.0.1:51740`.
- One parallel Docker instance on `https://127.0.0.1:51739` failed with a backend browser-state overlay timeout before prompt entry. This did not indicate a library-side schema, discovery, payload, or download failure; the second instance passed the same library tool flow.
- Compensating evidence for the failed instance: `https://127.0.0.1:51739/models/video` returned the expected model and the client reached `/generate-video`; failure text was a Playwright click timeout caused by a `cdk-overlay-backdrop` intercepting Gemini's prompt textbox.
- User waiver required: `No`; live validation passed on a real Docker LLM server instance and the failed instance is recorded as environment/browser-state instability.

## Residual Risk

- If a deployed server changes the video endpoint schema, the client boundary tests would need updating.
- If multiple `AUTOBYTEUS_LLM_SERVER_HOSTS` expose the same video model name, callers must set `DEFAULT_VIDEO_GENERATION_MODEL` to the host-qualified identifier; the ambiguous unqualified path intentionally fails with a clear error.
- Live RPA-backed video generation remains sensitive to Gemini App browser state and provider quota; the successful validation artifact is `/tmp/autobyteus-video-tool-live-51740/videos/live_tool_endpoint_smoke.mp4`.
