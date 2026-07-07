#!/bin/bash
# Submit the pubrun benchmark to LSF (via `bsub`).
#
# STARTING POINT — adapt to your site. Real clusters usually require a project (`-P`) and
# often a queue (`-q`)/walltime. This script submits to the default queue and lets the
# scheduler place the job. It is NOT validated against a live LSF cluster in CI.
#
# Usage:
#   benchmarks/submit_bench_lsf.sh                 # full run, default queue
#   benchmarks/submit_bench_lsf.sh --quick         # args forwarded to harness.py
#   PUBRUN_QUEUE=normal benchmarks/submit_bench_lsf.sh
#
# Configuration (environment; all optional):
#   PUBRUN_QUEUE     LSF queue (`-q`), if your site requires one.
#   PUBRUN_PROJECT   Project/allocation (`-P`), if required.
#   PUBRUN_PY        Python with pubrun importable (default: python3).
#   PUBRUN_REPO      Repo root (default: the repo containing this script).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
command -v bsub >/dev/null 2>&1 || { echo "ERROR: bsub not found (is LSF loaded?)." >&2; exit 1; }

export PUBRUN_BENCH_ARGS="${*:-}"
export PUBRUN_REPO="${PUBRUN_REPO:-$(cd "$HERE/.." && pwd)}"
export PUBRUN_PY="${PUBRUN_PY:-python3}"

# bsub options as an argv array (no shell interpolation of user values into a string).
BSUB_OPTS=(-J pubrun-bench -n 4 -W 30 -o "pubrun-bench-%J.out")
[ -n "${PUBRUN_QUEUE:-}" ]   && BSUB_OPTS+=(-q "$PUBRUN_QUEUE")
[ -n "${PUBRUN_PROJECT:-}" ] && BSUB_OPTS+=(-P "$PUBRUN_PROJECT")

# Job body piped to bsub on stdin (LSF reads the job script from stdin).
JOB_SCRIPT="$(cat <<'EOF'
#!/bin/bash
set -euo pipefail
cd "$PUBRUN_REPO"
RESULTS_DIR="$PUBRUN_REPO/benchmarks/results"
mkdir -p "$RESULTS_DIR"
NODE="$(hostname)"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT="$RESULTS_DIR/${NODE}-${STAMP}.json"
if ! "$PUBRUN_PY" -c "import pubrun" 2>/dev/null; then
    export PYTHONPATH="$PUBRUN_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
    "$PUBRUN_PY" -c "import pubrun" 2>/dev/null || {
        echo "ERROR: 'pubrun' not importable with $PUBRUN_PY; run '$PUBRUN_PY -m pip install -e $PUBRUN_REPO'." >&2
        exit 1; }
fi
# shellcheck disable=SC2086
"$PUBRUN_PY" benchmarks/harness.py --out "$OUT" $PUBRUN_BENCH_ARGS
echo "Done. Result: $OUT"
EOF
)"

echo "Submitting pubrun benchmark to LSF (default placement)..."
printf '%s\n' "$JOB_SCRIPT" | bsub "${BSUB_OPTS[@]}"
