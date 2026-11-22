#!/usr/bin/env python3
"""Maintainer-run tool: pull, validate, store, aggregate, and re-tag benchmark submissions.

Phase 2 of benchmark-intake (IPD 20260722-2209-01), the LOCAL PULL model. GitHub Actions gains
NO new powers and there is NO server write path: this script runs on the MAINTAINER's machine,
authenticated as the maintainer via `gh`. It:

  1. Lists benchmark-submission issues on the repo (via `gh`, argv only, never a shell).
  2. Resolves each submission's source the SAME way the server does (an allowlisted `.json`
     attachment/gist URL, or a single inline `pubrun-benchmark-submission:v1` JSON block).
  3. Downloads/reads it under the same host-allowlist + redirect + byte-cap protections, enforces
     a tightened 256 KB store cap BEFORE parsing, and runs the SAME fail-closed validation
     (schema /5 + share-safety + semantic) as the server, by IMPORTING the existing validator.
  4. Stores each accepted, redacted result content-addressed at
     benchmarks/data/accepted/<sha256>.json with a <sha256>.meta.json sidecar (dedupe by hash;
     the sidecar records ALL contributing issues in a `sources` list).
  5. Aggregates the accepted corpus locally via benchmarks/aggregate.py (summary.csv/summary.md).
  6. Re-tags issues status:accepted / status:needs-fix (always dropping status:pending), and
     comments ONLY on a rejection. `--dry-run` is the DEFAULT; `--apply` is required for any
     GitHub write or on-disk store. The script NEVER pushes and NEVER runs `gh auth login`.

Security posture (IPD S2-1..S2-7): untrusted JSON is parsed as DATA only (no eval/exec/pickle);
the 256 KB cap is enforced before parse; stored filenames are the SHA-256 of the validated bytes
(never derived from issue/attachment-supplied names) and are confined under the data dir; all
`gh` calls use argv lists with shell=False; tokens and payloads are never printed. This tool is
dev/reproducibility tooling and is NOT shipped in the pubrun wheel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent

# Import the ONE validation implementation (and the extractor + aggregator) rather than forking
# it, so local and server behavior stay in lockstep. These live in benchmarks/ and .github/scripts/
# (neither is a package), so prepend both dirs to sys.path, mirroring how
# validate_benchmark_submission.py itself imports share_safety.
sys.path.insert(0, str(_REPO / "benchmarks"))
sys.path.insert(0, str(_REPO / ".github" / "scripts"))
import validate_benchmark_submission as _v  # noqa: E402
import extract_attachment_url as _x  # noqa: E402
import aggregate as _agg  # noqa: E402

# Tightened store cap: refuse anything larger than this BEFORE parsing (a real redacted /5 result
# is ~38 KB, so ~6x headroom). Applied uniformly to URL and inline sources.
MAX_STORE_BYTES = 256 * 1024

_DEFAULT_REPO = "fariello/pubrun"
_SUBMISSION_LABEL = "type:benchmark-submission"
_DATA_SUBDIR = Path("data") / "accepted"

_LABEL_ACCEPTED = "status:accepted"
_LABEL_NEEDS_FIX = "status:needs-fix"
_LABEL_PENDING = "status:pending"

# Hidden marker embedded in every rejection comment so a repeated --apply run can recognize
# its own earlier comment and not post the same reason again.
_REJECT_MARKER = "<!-- pubrun-benchmark-pull-reject:v1 -->"

# A safe OWNER/NAME repo slug (blocks shell metacharacters even though we never use a shell).
import re  # noqa: E402
_GH_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class PullError(Exception):
    """A fatal, payload-free error."""


def _run_gh(args, *, timeout=60):
    """Run `gh` with an argv list (never a shell). Return stdout. Raise PullError on failure.
    Never prints tokens; callers must not pass secrets in argv."""
    try:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise PullError("GitHub CLI (gh) is not installed")
    except Exception as e:
        raise PullError(f"gh invocation failed: {type(e).__name__}")
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise PullError(tail[-1][:200] if tail else "gh returned non-zero")
    return proc.stdout


def _require_gh_ready() -> None:
    import shutil
    if shutil.which("gh") is None:
        raise PullError("GitHub CLI (gh) is not installed; see https://cli.github.com/")
    try:
        _run_gh(["auth", "status"], timeout=15)
    except PullError:
        raise PullError("gh is not authenticated; run `gh auth login` (this tool never does)")


def list_issues(repo: str, label: str, state: str, limit: int):
    """Return a list of issue dicts {number, url, author, body, labels} via gh (JSON)."""
    out = _run_gh(["issue", "list", "--repo", repo, "--label", label, "--state", state,
                   "--limit", str(int(limit)), "--json", "number,url,author,body,labels"])
    try:
        raw = json.loads(out) if out.strip() else []
    except ValueError:
        raise PullError("could not parse gh issue list output")
    issues = []
    for it in raw:
        issues.append({
            "number": it.get("number"),
            "url": it.get("url", ""),
            "author": (it.get("author") or {}).get("login", ""),
            "body": it.get("body") or "",
            "labels": [lb.get("name", "") for lb in (it.get("labels") or [])],
        })
    return issues


def _materialize_source(body: str, workdir: Path):
    """Resolve the submission in an issue body to a local file under workdir, enforcing the
    256 KB store cap uniformly (URL and inline) BEFORE parse. Return (path, kind, host) or raise
    _v.Reject with a payload-free reason."""
    kind, url, _file, error = _x.resolve_source(body)
    dest = workdir / "submission.json"
    if kind == "url":
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        # _download enforces host allowlist + bounded redirects + a 1 MiB cap; we then re-check
        # the tightened store cap below.
        _v._download(url, dest)
        if dest.stat().st_size > MAX_STORE_BYTES:
            raise _v.Reject("shape", f"submission exceeds the {MAX_STORE_BYTES}-byte store cap")
        return (dest, "url", host)
    if kind == "inline":
        payload, err = _x.find_inline_json(body)
        if not payload:
            raise _v.Reject("shape", err or "no inline JSON")
        if len(payload.encode("utf-8")) > MAX_STORE_BYTES:
            raise _v.Reject("shape", f"inline JSON exceeds the {MAX_STORE_BYTES}-byte store cap")
        dest.write_text(payload, encoding="utf-8")
        return (dest, "inline", "")
    raise _v.Reject("shape", error or "no submission source found in the issue")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def _accepted_dir(data_dir: Path) -> Path:
    return data_dir / "accepted"


def _confined(base: Path, name: str) -> Path:
    """Return base/name, guaranteeing the result stays under base (defense in depth even though
    name is a hex digest we compute, never attacker-supplied)."""
    base = base.resolve()
    target = (base / name).resolve()
    if base != target.parent:
        raise PullError("refusing to write outside the accepted/ directory")
    return target


def store_accepted(src: Path, data_dir: Path, *, issue_number, issue_url, submitter,
                   kind, host, apply: bool) -> tuple:
    """Store the validated result content-addressed; append this issue to the meta sidecar's
    `sources`. Return (sha, stored_bool, deduped_bool). With apply=False, computes but writes
    nothing."""
    import datetime
    sha = _sha256_file(src)
    acc = _accepted_dir(data_dir)
    # Store as *.redacted.json (the content passed share-safety) so the name advertises intent
    # and matches the repo convention that only *.redacted.json is trackable.
    json_path = _confined(acc, f"{sha}.redacted.json")
    meta_path = _confined(acc, f"{sha}.meta.json")
    deduped = json_path.exists()
    source_entry = {"issue_number": issue_number, "issue_url": issue_url,
                    "submitter_login": submitter}
    if not apply:
        return (sha, False, deduped)
    acc.mkdir(parents=True, exist_ok=True)
    if not deduped:
        json_path.write_bytes(Path(src).read_bytes())
    # Merge/append the source into the sidecar (keep all contributing issues; PR-002).
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except ValueError:
            meta = {}
    else:
        meta = {}
    meta.setdefault("sha256", sha)
    meta.setdefault("kind", kind)
    if host:
        meta.setdefault("source_host", host)
    meta.setdefault("fetched_utc", datetime.datetime.now(datetime.timezone.utc).isoformat())
    meta["validator_version"] = getattr(_v, "SCHEMA_MARKER", "pubrun-benchmark/5")
    meta["share_safety_version"] = _v.share_safety.SHARE_SAFETY_VERSION
    sources = meta.get("sources", [])
    if not any(s.get("issue_number") == issue_number for s in sources):
        sources.append(source_entry)
    meta["sources"] = sources
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return (sha, not deduped, deduped)


def aggregate_corpus(data_dir: Path, *, apply: bool) -> int:
    """Aggregate all stored accepted results into summary.csv/summary.md. Returns the row count.
    With apply=False, computes rows but writes nothing."""
    acc = _accepted_dir(data_dir)
    paths = sorted(str(p) for p in acc.glob("*.redacted.json"))
    runs = _agg._load(paths)
    rows = _agg.build_rows(runs)
    if apply:
        _agg.write_csv(rows, data_dir / "summary.csv")
        _agg.write_markdown(rows, data_dir / "summary.md")
    return len(rows)


def _existing_comment_bodies(repo: str, issue_number: int) -> list:
    """Return the bodies of the issue's existing comments, or [] when they cannot be read
    (gh failure, empty or non-JSON output). Never raises."""
    try:
        out = _run_gh(["issue", "view", str(int(issue_number)), "--repo", repo,
                       "--json", "comments"], timeout=30)
    except PullError:
        return []
    if not isinstance(out, str) or not out.strip():
        return []
    try:
        data = json.loads(out)
    except ValueError:
        return []
    comments = data.get("comments") if isinstance(data, dict) else None
    if not isinstance(comments, list):
        return []
    return [c.get("body") for c in comments
            if isinstance(c, dict) and isinstance(c.get("body"), str)]


def _already_commented(repo: str, issue_number: int, reason: str) -> bool:
    reason_line = f"- reason: {reason}"
    for body in _existing_comment_bodies(repo, issue_number):
        if _REJECT_MARKER in body and reason_line in body.splitlines():
            return True
    return False


def _retag(repo: str, issue_number: int, accepted: bool, reason: str, *, apply: bool) -> None:
    """Set the decision label, always dropping status:pending (PR-003). Comment ONLY on
    rejection, and only once per distinct reason. All writes are the maintainer's own gh
    actions; no-op unless apply."""
    add = _LABEL_ACCEPTED if accepted else _LABEL_NEEDS_FIX
    remove = _LABEL_NEEDS_FIX if accepted else _LABEL_ACCEPTED
    if not apply:
        return
    # issue_number is an int; labels are fixed constants; never a shell.
    num = str(int(issue_number))
    attempts = (
        ["--add-label", add, "--remove-label", remove, "--remove-label", _LABEL_PENDING],
        # The opposite decision label may not exist on the issue (gh refuses to remove an
        # absent label); still drop status:pending.
        ["--add-label", add, "--remove-label", _LABEL_PENDING],
        ["--add-label", add],
    )
    for extra in attempts:
        try:
            _run_gh(["issue", "edit", num, "--repo", repo, *extra], timeout=30)
            break
        except PullError:
            continue
    if not accepted:
        if _already_commented(repo, issue_number, reason):
            return
        body = (f"{_REJECT_MARKER}\n"
                "Automated (maintainer-run) benchmark check: needs fix.\n\n"
                f"- reason: {reason}\n\n"
                "Re-run `pubrun bench` (which writes a redacted file and share-checks it), then "
                "re-run `pubrun bench --contribute` or attach the redacted file, and edit the "
                "issue to resubmit.")
        try:
            _run_gh(["issue", "comment", num, "--repo", repo,
                     "--body", body], timeout=30)
        except PullError:
            pass


def _process_issue(repo: str, issue: dict, data_dir: Path, apply: bool, report: dict) -> None:
    num = issue["number"]
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        src = None
        kind = host = ""
        try:
            src, kind, host = _materialize_source(issue["body"], workdir)
            verdict = _v.validate_file(src)
        except _v.Reject as r:
            verdict = {"accepted": False, "stage": r.stage, "reason": r.reason}
        if verdict.get("accepted") and src is not None:
            sha, stored, deduped = store_accepted(
                src, data_dir, issue_number=num, issue_url=issue["url"],
                submitter=issue["author"], kind=kind, host=host, apply=apply)
            _retag(repo, num, True, "", apply=apply)
            entry = {"issue": num, "sha": sha, "stored": stored, "deduped": deduped}
            report["accepted"].append(entry)
            if deduped:
                report["deduped"].append(entry)
        else:
            reason = f"{verdict.get('stage', '?')}: {verdict.get('reason', 'invalid')}"
            _retag(repo, num, False, reason, apply=apply)
            report["rejected"].append({"issue": num, "reason": reason})


def process(repo: str, label: str, state: str, limit: int, data_dir: Path, apply: bool):
    """Main pipeline. Returns a report dict."""
    _require_gh_ready()
    issues = list_issues(repo, label, state, limit)
    report = {"repo": repo, "apply": apply, "processed": 0,
              "accepted": [], "rejected": [], "deduped": [], "errors": []}
    for issue in issues:
        report["processed"] += 1
        num = issue["number"]
        try:
            _process_issue(repo, issue, data_dir, apply, report)
        except Exception as exc:
            # An unexpected failure on one issue (transport error, malformed data, a bug) is
            # recorded without the payload and without relabeling the issue, and the batch
            # continues with the next issue.
            report["errors"].append({"issue": num, "reason": type(exc).__name__})
    if apply or True:
        report["aggregate_rows"] = aggregate_corpus(data_dir, apply=apply)
    return report


def _print_report(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    mode = "APPLIED" if report["apply"] else "DRY-RUN (no writes; re-run with --apply)"
    print(f"\nBenchmark submission pull [{mode}]  repo={report['repo']}", file=sys.stderr)
    print(f"  processed: {report['processed']}", file=sys.stderr)
    print(f"  accepted:  {len(report['accepted'])} "
          f"(deduped: {len(report['deduped'])})", file=sys.stderr)
    print(f"  rejected:  {len(report['rejected'])}", file=sys.stderr)
    for r in report["rejected"]:
        print(f"    - issue #{r['issue']}: {r['reason']}", file=sys.stderr)
    errors = report.get("errors", [])
    print(f"  errors:    {len(errors)}", file=sys.stderr)
    for e in errors:
        print(f"    - issue #{e['issue']}: {e['reason']}", file=sys.stderr)
    print(f"  aggregate rows: {report.get('aggregate_rows', 0)}", file=sys.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Pull, validate, store, aggregate, and re-tag benchmark submissions "
                    "(maintainer-run; dry-run by default).")
    ap.add_argument("--repo", default=_DEFAULT_REPO, metavar="OWNER/NAME",
                    help=f"target repo (default {_DEFAULT_REPO}).")
    ap.add_argument("--label", default=_SUBMISSION_LABEL,
                    help=f"issue label to pull (default {_SUBMISSION_LABEL}).")
    ap.add_argument("--state", default="open", choices=("open", "closed", "all"),
                    help="issue state to pull (default open).")
    ap.add_argument("--limit", type=int, default=100, help="max issues to process (default 100).")
    ap.add_argument("--data-dir", default=str(_HERE / "data"),
                    help="local corpus directory (default benchmarks/data).")
    ap.add_argument("--apply", action="store_true",
                    help="actually store results and re-tag/comment on issues "
                         "(default is a dry run that writes nothing).")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="emit the report as JSON on stdout.")
    args = ap.parse_args(argv)

    if not _GH_REPO_RE.match(args.repo):
        print(f"Invalid --repo {args.repo!r}; expected OWNER/NAME.", file=sys.stderr)
        return 2
    try:
        report = process(args.repo, args.label, args.state, args.limit,
                         Path(args.data_dir), args.apply)
    except PullError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    _print_report(report, args.as_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
