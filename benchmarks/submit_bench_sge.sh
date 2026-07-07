#!/bin/bash
# Submit the pubrun benchmark to SGE / Grid Engine (UGE/OGE) (via `qsub`).
#
# STARTING POINT — adapt to your site. SGE sites vary a lot: many require a parallel
# environment (`-pe <pe> <n>`), a project (`-P`), and/or a queue (`-q`). This script submits
# a minimal single-slot job and lets the scheduler place it. It is NOT validated against a
# live SGE cluster in CI. NOTE: SGE and PBS both use `qsub` — use `--scheduler sge` if
# auto-detection is ambiguous.
#
# Usage:
#   benchmarks/submit_bench_sge.sh                 # full run
#   benchmarks/submit_bench_sge.sh --quick         # args forwarded to harness.py
#   PUBRUN_QUEUE=all.q benchmarks/submit_bench_sge.sh
#
# Configuration (environment; all optional):
#   PUBRUN_QUEUE     SGE queue (`-q`), if your site requires one.
#   PUBRUN_PE        Parallel environment + slots, e.g. "smp 4" (`-pe`), if required.
#   PUBRUN_PY        Python with pubrun importable (default: python3).
#   PUBRUN_REPO      Repo root (default: the repo containing this script).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
command -v qsub >/dev/null 2>&1 || { echo "ERROR: qsub not found (is SGE/Grid Engine loaded?)." >&2; exit 1; }

export PUBRUN_BENCH_ARGS="${*:-}"
export PUBRUN_REPO="${PUBRUN_REPO:-$(cd "$HERE/.." && pwd)}"
export PUBRUN_PY="${PUBRUN_PY:-python3}"

# qsub options as an argv array (no shell interpolation of user values into a string).
# -cwd run in current dir; -j y merge stderr; -V export environment; -N job name.
QSUB_OPTS=(-N pubrun-bench -cwd -j y -V -l "h_rt=00:30:00")
[ -n "${PUBRUN_QUEUE:-}" ] && QSUB_OPTS+=(-q "$PUBRUN_QUEUE")
if [ -n "${PUBRUN_PE:-}" ]; then
    # PUBRUN_PE is "pe_name slots"; split intentionally into two argv elements.
    # shellcheck disable=SC2086
    QSUB_OPTS+=(-pe ${PUBRUN_PE})
fi

# Job body piped to qsub on stdin.
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

echo "Submitting pubrun benchmark to SGE (default placement)..."
printf '%s\n' "$JOB_SCRIPT" | qsub "${QSUB_OPTS[@]}"
