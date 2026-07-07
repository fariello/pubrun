#!/bin/bash
# Submit the pubrun benchmark to PBS / Torque / OpenPBS (via `qsub`).
#
# STARTING POINT — adapt to your site. Real clusters usually require an account/allocation
# (`#PBS -A <acct>`) and often a specific queue/walltime. This script submits to the default
# queue and lets the scheduler place the job (portable; no site-specific idle-node query).
# It is NOT validated against a live PBS cluster in CI.
#
# Usage:
#   benchmarks/submit_bench_pbs.sh                 # full run, default queue
#   benchmarks/submit_bench_pbs.sh --quick         # args forwarded to harness.py
#   PUBRUN_QUEUE=workq benchmarks/submit_bench_pbs.sh
#
# Configuration (environment; all optional):
#   PUBRUN_QUEUE     PBS queue (`-q`), if your site requires one.
#   PUBRUN_ACCOUNT   Account/allocation (`-A`), if required.
#   PUBRUN_PY        Python with pubrun importable (default: python3).
#   PUBRUN_REPO      Repo root (default: the repo containing this script).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
command -v qsub >/dev/null 2>&1 || { echo "ERROR: qsub not found (is PBS/Torque loaded?)." >&2; exit 1; }

export PUBRUN_BENCH_ARGS="${*:-}"
export PUBRUN_REPO="${PUBRUN_REPO:-$(cd "$HERE/.." && pwd)}"
export PUBRUN_PY="${PUBRUN_PY:-python3}"

# Build qsub options as an argv array (no shell interpolation of user values into a string).
QSUB_OPTS=(-N pubrun-bench -l "select=1:ncpus=4:mem=4gb" -l "walltime=00:30:00"
           -j oe -V)
[ -n "${PUBRUN_QUEUE:-}" ]   && QSUB_OPTS+=(-q "$PUBRUN_QUEUE")
[ -n "${PUBRUN_ACCOUNT:-}" ] && QSUB_OPTS+=(-A "$PUBRUN_ACCOUNT")

# Job body: run the harness on the assigned node, write a node-tagged result JSON.
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

echo "Submitting pubrun benchmark to PBS (default placement)..."
printf '%s\n' "$JOB_SCRIPT" | qsub "${QSUB_OPTS[@]}"
