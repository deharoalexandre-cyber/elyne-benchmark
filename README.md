# Elyne Benchmark

Public, three-arm benchmark for measuring what a persistent local-AI substrate adds to a fixed language-model binding.

This repository publishes the benchmark instrument, frozen scoring logic, selected public evidence, and an adapter protocol. It does **not** publish Elyne Next's private runtime, prompts, ledgers, databases, or internal tool catalogue.

## Experimental question

Holding the model binding, sampling parameters, and seed constant, what changes when only the information substrate varies?

| Arm | Input available to the same binding | Purpose |
|---|---|---|
| `core-origin` | Full system under test: durable state, retrieval, time, and authorized tools | Measures the integrated substrate |
| `gemma-info` | The exact information surfaced by the substrate, without its orchestration or tools | Separates information access from orchestration |
| `gemma-nu` | User prompt only | Bare-model control |

An adapter must attest one identical `binding_sha256` and one identical `sampling_sha256` for every item and every arm. The harness fails closed if those identities diverge.

## Frozen batteries

| Family | Cases | What it probes | Reference result (`core / info / bare`) |
|---|---:|---|---:|
| `justesse` | 17 | reasoning controls, memory, RAG, time, tools | `15/15 · 14/15 · 6/15` on objectively scored items; 2 judge items pending |
| `orchestration` | 14 | consolidation, revision, interruption, inter-session persistence, selection, tool use | `13/14 · 12/14 · 0/14` |
| `toolchain` | 15 | exact two-step acquisition chains with opaque targets | `15/15 · 0/15 · 0/15` |

These are reference observations from one deterministic campaign, not universal performance estimates. See [LIMITATIONS.md](LIMITATIONS.md).

## Verify the published artifact

Requirements: Python 3.11+ and `jsonschema==4.26.0`.

```bash
python -m pip install -r requirements.lock
python scripts/verify_report.py
python -m unittest discover -s tests -v
```

Verification checks fixture schemas, copied source hashes, the frozen matcher, evidence commitments, response hashes, re-scored outcomes, aggregate totals, reference reports, and every file in `release-manifest.json`.

## Run a replication

The harness is independent of Elyne Corp code. The system under test is connected through three JSON subprocess adapters described in [ADAPTER_PROTOCOL.md](ADAPTER_PROTOCOL.md).

First validate the protocol locally:

```bash
python scripts/run_benchmark.py --family toolchain --adapter-config adapters/mock.config.json
```

The mock adapter only exercises the protocol. Its scores are synthetic and must never be reported as model results.

For an actual replication:

1. Implement a substrate-aware `core-origin` adapter.
2. Use `adapters/openai_compatible.py` for the two direct control arms, or implement equivalent adapters.
3. Copy `adapters/template.config.json`, point each command to the correct adapter, and lock the environment variables documented in [ADAPTER_PROTOCOL.md](ADAPTER_PROTOCOL.md).
4. Run each family with `scripts/run_benchmark.py`.
5. Publish the resulting `report.json`, campaign manifest, adapter code, model-binding identity, sampling identity, and environment description.

```bash
python scripts/run_benchmark.py --family justesse --adapter-config adapters/my.config.json
python scripts/run_benchmark.py --family orchestration --adapter-config adapters/my.config.json
python scripts/run_benchmark.py --family toolchain --adapter-config adapters/my.config.json
```

Outputs are written under `runs/local/` and are never silently overwritten.

## Integrity anchors

| Artifact | SHA-256 |
|---|---|
| Frozen tool-chain matcher | `56736f207a207dc04b5262996160c54d367be4e99f0d670adc700a3d61317260` |
| Justesse battery | `8c4dc5b71c668c7d272cb1cc5003d1dc1692a0a08565e79c9c75d8f354eebbdc` |
| Orchestration battery | `2a9ccb875da2becfdee49947dc018e3c04f8132ae7bfac6d01d962244aa8191b` |
| Tool-chain battery | `acd16d43554595d0df497853ebf3d086da6f7e0b8d0a1d6336bc8adcd4c10e4a` |
| Justesse reference report | `05be9255c66542c35d784eea1eda092153d2378c23f4f53bd2edf812a1b59f84` |
| Orchestration reference report | `7d323969f58bbe2f027bc23164abfea07a7566caba38981637a0745a2da7342b` |
| Tool-chain reference report | `14931ee92528780b2436ce530c8d43094d098a9d37e1e8a8064400d107bffb96` |

## Reading order

- [METHODOLOGY.md](METHODOLOGY.md): design, contrasts, scoring, and interpretation.
- [ADAPTER_PROTOCOL.md](ADAPTER_PROTOCOL.md): how to connect another system.
- [BENCHMARK_HISTORY.md](BENCHMARK_HISTORY.md): errors found while trying to break the benchmark.
- [LIMITATIONS.md](LIMITATIONS.md): what the evidence does and does not establish.
- [PUBLICATION_AUDIT.md](PUBLICATION_AUDIT.md): what was deliberately excluded from this public artifact.

## License and citation

Software is licensed under Apache-2.0. Benchmark batteries, reports, evidence, and documentation are licensed under CC-BY-4.0. See [LICENSE](LICENSE) for the exact scope and [CITATION.cff](CITATION.cff) for citation metadata.
