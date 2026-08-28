# Publication audit

Audit record:

- case-level audit: Claude Code, 2026-08-28;
- harness remediation and evidence re-verification: Codex, 2026-08-28;
- publication authorization: Alexandre De Haro;
- scope: all 46 frozen cases, with a focused correction of the two orchestration tool cases.

This is a named cross-review by the two development agents, not an independent
third-party certification. Independent replication and audit remain invited.

This repository follows a “publish the instrument, not the private system” boundary.

Included:

- frozen case catalogues and batteries;
- copied case-generator sources required by fixture commitments;
- schemas and exact scoring code;
- public reference reports and judge keys;
- per-case JSON evidence referenced by those reports;
- adapter protocol and independent runner;
- release-wide file manifest.

Excluded:

- Elyne Next runtime and application source;
- system prompts and full model request envelopes;
- private conversation journals and memory stores;
- SQLite projections and append-only ledgers;
- credentials, endpoint secrets, user documents, and local paths not required by the benchmark;
- complete internal tool catalogue and authority policy;
- binary proof bundles whose contents disclose the excluded material.

The selected reports refer only to copied public JSON evidence. The verifier rejects missing or modified evidence. Where a public report commits to a source or matcher, the corresponding exact file is present.

The 2026-08-28 audit found that the two orchestration tool cases could be
answered from general knowledge and that the v1 score did not prove both tool
calls. They were replaced in battery revision 2 by opaque local chains. The
orchestration report now commits to the frozen tool-chain matcher and publishes
the exact ordered traces used to recompute all six causal dimensions. The old
reference run remains in Git history and under its original campaign directory;
its figures were not rewritten.

The publication package was scanned for local paths, credentials, API keys, email addresses, and unintended private names before release. The approved dual-license boundary is recorded in [LICENSE](LICENSE).
