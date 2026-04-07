# pubrun Roadmap & Open Requirements

## Target Pre-v0.2 Actions

### 1. Advanced Post-Execution API Documentation
We need to generate a deeply structural `readthedocs.io` compliant MkDocs or Sphinx integration focusing purely on Python module integration, hook usage, decorators, and data extraction patterns.
- *Status*: Pending 

### 2. Subprocess Argument Redaction
Currently, the `SubprocessSpy` engine effectively intercepts `subprocess.run(["curl", "-H", "Authorization: Bearer 123..."])` but blindly documents it in plaintext directly into the `manifest.json`.
- *Architecture Debate*: Implementing a hardcoded Regex Redaction masking engine (e.g. searching for `/password|bearer|secret/i`) might accidentally severely mutilate clean scientific outputs (e.g., `--output=secret_findings.csv`). We need to determine the safest possible architecture before finalizing a default enforcement policy.
- *Status*: Pending Community Input / Discussion.
