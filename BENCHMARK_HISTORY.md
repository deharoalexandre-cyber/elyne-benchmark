# Benchmark history

The benchmark was hardened by preserving failures in the measurement process instead of hiding them.

## v0 — accent false negative

A tool/RAG answer quoted the source correctly, but the expected substring used `fabriquée` while the source used `fabriquee`. The answer was incorrectly marked as a failure. The fixture was aligned to the actual source and committed (`a9371ad` in the originating repository). Lesson: a matcher typo can dominate a tiny benchmark.

## v1 — substring false positive

A permissive `contains` rule could award a point when the expected token appeared incidentally inside an explanation or example. This is especially unsafe for procedural tool tests. Lesson: presence of a word is not proof of acquisition, causality, or final-answer correctness.

## v2 — interruption artifact

An earlier interruption construction did not isolate persistence cleanly enough. It was replaced with explicit session traces and real restart evidence in the orchestration battery. Lesson: a narrative claim of continuity must be backed by a state transition that the harness can inspect.

## v3 — frozen exact tool-chain

The tool-chain sub-benchmark introduced per-case opaque tokens, exactly two causally linked acquisitions, canonical argument comparison, strict JSON, NFC-normalized exact targets, and rejection of parasitic calls. Its matcher was frozen before the reference run:

`56736f207a207dc04b5262996160c54d367be4e99f0d670adc700a3d61317260`

A later authority ambiguity between generic text reading and workspace reading was resolved by requiring `read_workspace_file`; the matcher itself did not change (`9d896ec` in the originating repository).

The public verifier recomputes scores from the frozen matcher and evidence. A cosmetically cleaned report is therefore insufficient: the committed inputs and traces must agree.

