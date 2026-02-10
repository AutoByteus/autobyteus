# Simulated Runtime Call Stacks (Debug-Trace Style)

## Simulation Basis

- Scope: `Small`
- Source: `docs/implementation-plan.md`

## Use Case 1: Explicit Vertex Provider

```text
[ENTRY] autobyteus/tools/search_tool.py:Search.__init__(...)
├── autobyteus/tools/search/factory.py:SearchClientFactory.create_search_client()
│   ├── read env + provider flags [STATE]
│   ├── provider_name == SearchProvider.VERTEX_AI_SEARCH -> VertexAISearchStrategy() [STATE]
│   └── autobyteus/tools/search/client.py:SearchClient.__init__(strategy) [STATE]
└── [ASYNC] autobyteus/tools/search_tool.py:Search._execute(...)
    └── [ASYNC] autobyteus/tools/search/client.py:SearchClient.search(...)
        └── [ASYNC] autobyteus/tools/search/vertex_ai_search_strategy.py:VertexAISearchStrategy.search(...)
            ├── build endpoint/payload [STATE]
            └── [IO] aiohttp POST ... :searchLite
```

Fallback/Error:

```text
[ERROR] autobyteus/tools/search/vertex_ai_search_strategy.py:VertexAISearchStrategy.__init__(...)
└── raise ValueError when VERTEX_AI_SEARCH_API_KEY or VERTEX_AI_SEARCH_SERVING_CONFIG is missing/invalid
```

## Use Case 2: Fallback Order

```text
[ENTRY] autobyteus/tools/search/factory.py:SearchClientFactory.create_search_client()
├── if explicit provider missing config -> ValueError [ERROR]
├── fallback chain:
│   1) Serper if configured
│   2) SerpApi if configured
│   3) Vertex AI Search if configured
└── else -> ValueError("No search provider is configured")
```

## Use Case 3: Removed google_cse

```text
[ENTRY] autobyteus/tools/search/factory.py:SearchClientFactory.create_search_client()
└── provider_name == "google_cse" -> ValueError("... no longer supported ...")
```

## Cleanliness Check

- End-to-end feasibility: Pass
- Separation of concerns: Pass
- Dependency flow: Pass
- Major smell detected: No
