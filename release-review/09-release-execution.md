# 09 Release Execution (Post-Go)

## Purpose

Execute the actual repository release packaging, version tagging, validation, and PyPI publishing *after* the "GO" or "CONDITIONAL GO" decision has been explicitly approved by the user at the end of Section 8.

---

## Standing Constraints for this Section

- You MUST NOT skip any step in this checklist.
- You MUST wait for and inspect remote CI execution output before building final package targets.
- You MUST verify that the built package contains the correct embedded git commit hash matching the release commit.
- You MUST recreate tags as annotated/signed release tags (not lightweight tags) before pushing them.

---

## Step-by-Step Release Execution Checklist

### 1. Finalize, Commit, and Push Code
Ensure that all code changes, version bumps, and documentation (such as `CHANGELOG.md`) are committed locally and that the working directory is clean. Push the local release branch to the remote origin:
```bash
git push origin main
```
*(or the designated release branch)*

### 2. Verify Remote CI/Actions Output
Wait for and query the remote repository's CI checks (e.g., GitHub Actions) to verify that they pass successfully for the pushed commit hash.
- **Monitoring CI**: Propose `gh run watch <run-id>` or `gh run list --limit 5` commands via `run_command`.
- **Background Run**: If monitoring runs in the background, check the task status or schedule a wait timer.
- **CRITICAL**: Do not proceed to package building if any CI check fails. If failures occur, fix the issue, commit/push, and restart this step.

### 3. Bake Commit Metadata & Build Packages
Once remote CI is 100% green, build the distribution package targets (wheel and sdist):
```bash
python -m build
```
*(Note: Running this command automatically triggers the custom Hatch build hook defined in `hatch_build.py`, writing the exact release commit hash to `src/pubrun/COMMIT` before packaging.)*

### 4. Verify the Baked Commit in the Built Artifact
Confirm that the commit hash inside the generated wheel is correct and matches the HEAD git commit hash exactly.
- **Check Commands**:
  ```bash
  # Extract and show the baked COMMIT file inside the wheel
  unzip -p dist/*.whl pubrun/COMMIT
  # Show HEAD commit hash
  git rev-parse HEAD
  ```
- **Acceptance Criteria**: Verify that the output of both commands matches perfectly. If there is any mismatch (e.g., fallback grace triggering a blank or stale commit), delete `dist/`, clean up, and rebuild.

### 5. Tag the Release
Create an annotated release tag matching the version (e.g. `v1.2.0`) on the final commit, and push the tag to the remote origin.
- **Check for Existing Tags**: If a lightweight or stale tag already exists locally for this version, delete it first:
  ```bash
  git tag -d v1.2.0
  ```
- **Create and Push Annotated Tag**:
  ```bash
  git tag -a v1.2.0 -m "Release v1.2.0"
  git push origin v1.2.0
  ```
- **Acceptance Criteria**: Confirm that the command succeeds and the new tag is listed in the remote repository.

### 6. Twine Validation
Run check validation on the built packages:
```bash
twine check dist/*
```
- **Acceptance Criteria**: Both the source distribution (`.tar.gz`) and binary distribution (`.whl`) must report `PASSED`.

### 7. Publish to PyPI (Twine Upload)
Upload the final verified distribution files to PyPI:
```bash
twine upload dist/*
```

#### Handling Interactive Prompts & Credentials
Because PyPI publishing typically prompts for user credentials or API tokens, follow these strict execution rules:
- **Interactive Check**: If you launch the command as a background task, check the status or log output.
- **Prompt Detection**: If the task prompts for an API token or password (`Enter your API token:`), you must:
  1. Notify the user immediately in the chat that the command is waiting for input.
  2. Provide the user with two options:
     - **Option A**: Provide the token/credentials directly in the chat, which you will send to the command using `send_input`.
     - **Option B**: Cancel the background task and hand the publish step off to the user to run directly in their own local terminal.
- **Task Cancellation**: If the user prefers Option B, cancel the task using `manage_task` with action `kill`, and record the handoff in `task.md` and `walkthrough.md`.

---

## Exit Criteria

The release execution is complete only when:
1. The release branch has been pushed and verified on the remote repository.
2. All remote CI checks have passed.
3. The package distribution files are built and contain the correct baked commit.
4. The annotated release tag has been pushed to the remote repository.
5. Twine validation passes.
6. The packages have been successfully uploaded to PyPI (or officially handed off to the user).
