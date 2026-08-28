# Methodology

## Claim under test

The benchmark tests a narrow causal claim: for one fixed model binding, deterministic sampling configuration, and seed, an external substrate can improve factual continuity, retrieval, temporal grounding, and multi-step tool execution. It does not test whether one foundation model is intrinsically better than another.

The unit of comparison is a three-arm triplet executed for every case:

1. `core-origin` runs the complete system under test.
2. `gemma-info` receives the information made available by the substrate, but not its state-management machinery or tools.
3. `gemma-nu` receives only the user question.

This yields three descriptive contrasts:

- `core-origin − gemma-nu`: total observed substrate contribution;
- `core-origin − gemma-info`: orchestration/action contribution after information access is controlled;
- `gemma-info − gemma-nu`: information-access contribution.

The arithmetic differences are descriptive for these fixed cases. They are not confidence intervals or population estimates.

## Fairness invariants

Every replication must keep these values identical across all arms and cases:

- exact model and inference binding, committed as `binding_sha256`;
- decoding/sampling configuration, committed as `sampling_sha256`;
- seed `0`;
- case battery and source hashes.

Only context mode varies. Direct controls have no tools. For `justesse`, the information-only material is captured from what the core actually surfaced and is hash-echoed by the control adapter. For the other batteries, the predeclared raw control material is replayed and committed.

## Families

### Justesse

Seventeen items cover unassisted reasoning controls, memory, RAG, temporal facts, and tool-grounded answers. Twelve items use objective matching, three require tools, and two qualitative synthesis/reasoning items remain explicitly judge-scored. Judge-pending items are excluded from the objective denominator.

### Orchestration

Fourteen items probe whether raw observations become usable through consolidation, revision, interruption recovery, real inter-session restart, memory selection, and tool-mediated acquisition. In revision 2, both tool cases use opaque planted local data and the same six-dimensional exact matcher as the dedicated tool-chain family. Every arm is scored by that matcher; direct controls are not forced to fail by arm identity.

### Tool-chain

Fifteen cases use three families of two-step causal chains (`list-read`, `route-document`, `search-read`) and opaque per-case identifiers. Six dimensions are scored:

- first tool and exact arguments;
- second tool and exact arguments;
- causal order;
- integration of the second result;
- exact final target;
- absence of parasitic calls.

The matcher parses a strict one-key JSON object, normalizes NFC, requires the exact target, compares canonical JSON arguments, and requires exactly two completed calls. Substring scoring is forbidden.

## Evidence and verification

Fixtures, catalogues, copied case generators, schemas, the tool-chain matcher, reports, and selected evidence are content-addressed. `scripts/verify_report.py` re-computes hashes and scores rather than trusting the published aggregate.

The public package contains the JSON evidence needed to inspect reported answers, replay material, planted sources, session traces, and tool traces. Binary runtime proofs and private journals remain outside the public artifact; their exclusion is documented in [PUBLICATION_AUDIT.md](PUBLICATION_AUDIT.md).

## Replication standard

A result should be described as a replication only if the implementer publishes:

- the unmodified frozen batteries and matcher;
- all three adapter implementations or an auditable equivalent;
- the exact binding and sampling identities;
- the generated requests, observations, report, and manifest;
- hardware, runtime, model file/hash, and relevant dependency versions;
- all deviations from this protocol.

Changing an item, matcher, decoding parameter, or model creates a new experiment and must receive new hashes.

Recomputing a published report from its public JSON is a verification of the
instrument and recorded observations. It is not a reconstruction of the private
Elyne Next runtime, whose prompts, envelopes, journals, and binary proofs are
deliberately outside this package.
