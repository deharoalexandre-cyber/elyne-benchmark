# Adapter protocol

The public runner communicates with each arm through a subprocess. The command receives one UTF-8 JSON document on standard input, emits exactly one UTF-8 JSON document on standard output, writes diagnostics only to standard error, and exits with code `0` on success.

Commands are argv arrays, never shell strings. They run with the repository root as their working directory.

## Configuration

```json
{
  "schema": "elyne.benchmark.adapter-config/v1",
  "commands": {
    "core-origin": ["python", "adapters/my_core.py"],
    "gemma-info": ["python", "adapters/openai_compatible.py"],
    "gemma-nu": ["python", "adapters/openai_compatible.py"]
  }
}
```

The exact three commands are required.

## Request

Each adapter receives:

```json
{
  "schema": "elyne.benchmark.adapter-request/v1",
  "family": "justesse",
  "campaign_id": "32-lowercase-hex",
  "item_id": "mem-01",
  "subject_id": "core-origin",
  "seed": 0,
  "case": {},
  "control_material": null,
  "control_material_sha256": null
}
```

The `case` value is the complete frozen case. The core adapter must apply its setup in an isolated case state. It must not leak state across cases except where the case explicitly defines a multi-turn or inter-session sequence.

## Observation

The response has a closed shape; extra and missing keys are rejected:

```json
{
  "schema": "elyne.benchmark.adapter-observation/v1",
  "family": "justesse",
  "item_id": "mem-01",
  "subject_id": "core-origin",
  "status": "completed",
  "reason_code": null,
  "response_text": "...",
  "tool_calls": [],
  "tool_trace": [],
  "binding_sha256": "64-lowercase-hex",
  "sampling_sha256": "64-lowercase-hex",
  "context_mode": "substrate",
  "tools_declared": true,
  "received_material_sha256": null,
  "surfaced_information": {}
}
```

Context modes are fixed:

| Family | `core-origin` | `gemma-info` | `gemma-nu` |
|---|---|---|---|
| justesse | `substrate` | `information-only` | `user-only` |
| orchestration | `substrate` | `raw-information-only` | `user-only` |
| toolchain | `substrate` | `initial-information-only` | `user-only` |

Direct controls must set `tools_declared=false` and return empty tool calls/traces. A completed observation has string `response_text` and null `reason_code`; a failed one has null response and a stable string reason code.

For the `justesse` core, `surfaced_information` must be the exact structured material exposed to the model. The runner feeds that object to `gemma-info`. All other arms return `null` in this field. Every adapter echoes the supplied material commitment in `received_material_sha256`.

Tool-chain core traces, including the two `orchestration` cases whose `case_type` is `tool`, must preserve call order and include the exact tool identifier, arguments, completion outcome, canonical-argument hash, result hash, and the second-result target attestation. The frozen matcher remains the authority. Direct controls submit empty traces to the same matcher; they are not assigned failure by convention.

## OpenAI-compatible direct controls

`adapters/openai_compatible.py` intentionally supports only `gemma-info` and `gemma-nu`. A chat endpoint cannot attest that substrate setup, durable state, retrieval, and tools were actually applied, so it refuses `core-origin`.

Required environment variables:

- `ELYNE_BENCH_BASE_URL` — endpoint root;
- `ELYNE_BENCH_MODEL` — model identifier;
- `ELYNE_BENCH_BINDING_SHA256` — exact shared model/inference binding commitment.

Optional variables are `ELYNE_BENCH_API_KEY`, `ELYNE_BENCH_MAX_TOKENS` (default `1536`), and `ELYNE_BENCH_HTTP_TIMEOUT` (default `600`). The adapter uses temperature `0`, top-p `1`, seed `0`, and non-streamed chat completions.

The core adapter and direct controls must compute the same sampling commitment. A full replication may replace this bundled adapter if its endpoint does not honor these fields, but must document the equivalent deterministic configuration.
