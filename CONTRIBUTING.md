# Contributing replications

Do not edit frozen fixtures, reference reports, or the matcher in place. A change creates a new revision and new hashes.

A replication contribution should include:

- a unique campaign ID;
- adapter source and configuration with secrets removed;
- model file/hash and inference-runtime version;
- hardware and operating-system description;
- binding and sampling commitments;
- generated report and manifest;
- any protocol deviation;
- the output of `python scripts/verify_report.py`.

Never commit API keys, private memory, conversation logs, proprietary documents, or unrestricted runtime dumps.

Use a new directory under `runs/replications/<organization>/<campaign-id>/`. `runs/local/` is ignored and intended for experiments.

