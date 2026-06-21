# 09 Release Execution (Post-Go)

## Purpose

Execute the actual repository release packaging, version tagging, validation, and PyPI publishing *after* the "GO" or "CONDITIONAL GO" decision has been explicitly approved by the user.

## Standing constraints for this section

- You MUST NOT skip any step in this checklist.
- You MUST wait for and inspect remote CI execution output before building final package targets.
- You MUST verify that the built package contains the correct embedded git commit hash matching the release commit.

## Step-by-Step Release Execution Checklist

### 1. Finalize, Commit and Push Code
Ensure that all code changes, version bumps, and documentation (such as CHANGELOG.md) are committed locally. Push the release branch to the remote origin:
```bash
git push origin main
```
*(or the designated release branch)*

### 2. Verify Remote CI/Actions Output
Wait/query the remote repository's CI checks (e.g. GitHub Actions) to verify that they pass successfully for the pushed commit hash.
- Run `gh run list --limit 5` or similar commands to monitor the status of the CI run.
- **CRITICAL**: Do not proceed to package building if any CI check fails. If failures occur, fix the issue, commit/push, and restart this step.

### 3. Bake Commit Metadata & Build Packages
Once CI is 100% green, build the distribution package targets (wheel and sdist):
```bash
python -m build
```
*(Running the build backend automatically triggers the custom Hatch build hook to write the exact release commit hash to `src/pubrun/COMMIT` before packaging.)*

### 4. Verify the Baked Commit in the Built Artifact
Confirm that the commit hash inside the generated wheel is correct and matches the HEAD git commit hash exactly:
```bash
# Extract and show the baked COMMIT file
unzip -p dist/*.whl pubrun/COMMIT
# Show HEAD commit hash
git rev-parse HEAD
```
Verify that the output of both commands matches perfectly.

### 5. Tag the Release
Create a signed/annotated git release tag matching the version (e.g. `v1.1.2`) on the final commit, and push the tag to the remote origin:
```bash
git tag -a v1.1.2 -m "Release v1.1.2"
git push origin v1.1.2
```

### 6. Twine Validation
If twine is available, run check validation on the built packages:
```bash
twine check dist/*
```

### 7. Publish to PyPI
Upload the final verified distribution files to PyPI:
```bash
twine upload dist/*
```

## Exit criteria

The release execution is complete only when the branch has been pushed, CI checks have passed, the baked commit has been verified, the release tag has been pushed, and package distribution artifacts are uploaded/published.
