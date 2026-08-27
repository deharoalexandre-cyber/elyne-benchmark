# Publication audit

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

Before pushing, the owner should still review the case text and recorded model responses for disclosure and select a license. This repository has not been uploaded automatically.

