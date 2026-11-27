#!/bin/bash
# Submit the pubrun benchmark to SGE / Grid Engine (UGE/OGE) (via `qsub`).
#
# STARTING POINT -- adapt to your site. SGE sites vary a lot: many require a parallel
# environment (`-pe <pe> <n>`), a project (`-P`), and/or a queue (`-q`). This script submits
# a minimal single-slot job and lets the scheduler place it. It is NOT validated against a
# live SGE cluster in CI. NOTE: SGE and PBS both use `qsub` -- use `--scheduler sge` if
# auto-detection is ambiguous.
#
# Usage:
#   submit_bench_sge.sh                 # full run
#   submit_bench_sge.sh --quick         # args forwarded to pubrun._bench.harness
#   PUBRUN_QUEUE=all.q submit_bench_sge.sh
#
# Configuration (environment; all optional):
#   PUBRUN_QUEUE         SGE queue (`-q`), if your site requires one.
#   PUBRUN_PE            Parallel environment + slots, e.g. "smp 4" (`-pe`), if required.
#   PUBRUN_PY            Python with pubrun importable (default: python3).
#   PUBRUN_REPO          Optional pubrun source checkout root (empty by default).
#   PUBRUN_RESULTS_DIR   Writable directory for benchmark result JSON files.
#   PUBRUN_REDACTED_OUT  Explicit output path for the share-safe redacted JSON.
#   PUBRUN_UNREDACTED    Non-empty to also write an identifying unredacted copy.
set -euo pipefail

command -v qsub >/dev/null 2>&1 || { echo "ERROR: qsub not found (is SGE/Grid Engine loaded?)." >&2; exit 1; }

export PUBRUN_BENCH_ARGS="${*:-}"
export PUBRUN_REPO="${PUBRUN_REPO:-}"
export PUBRUN_PY="${PUBRUN_PY:-python3}"

if [ -n "${PUBRUN_RESULTS_DIR:-}" ]; then
    PUBRUN_RESULTS_DIR="$PUBRUN_RESULTS_DIR"
elif [ -n "$PUBRUN_REPO" ] && [ -d "$PUBRUN_REPO/benchmarks" ]; then
    PUBRUN_RESULTS_DIR="$PUBRUN_REPO/benchmarks/results"
else
    PUBRUN_RESULTS_DIR="${PWD}/pubrun-bench-results"
fi
case "$PUBRUN_RESULTS_DIR" in
    /*) ;;
    *)  PUBRUN_RESULTS_DIR="${PWD}/${PUBRUN_RESULTS_DIR}" ;;
esac
export PUBRUN_RESULTS_DIR
export PUBRUN_REDACTED_OUT="${PUBRUN_REDACTED_OUT:-}"
export PUBRUN_UNREDACTED="${PUBRUN_UNREDACTED:-}"

# qsub options as an argv array (no shell interpolation of user values into a string).
# -cwd run in current dir; -j y merge stderr; -V export environment; -N job name.
QSUB_OPTS=(-N pubrun-bench -cwd -j y -V -l "h_rt=00:30:00")
if [ -n "${PUBRUN_QUEUE:-}" ]; then
    QSUB_OPTS+=(-q "$PUBRUN_QUEUE")
fi
if [ -n "${PUBRUN_PE:-}" ]; then
    # PUBRUN_PE is "pe_name slots"; split intentionally into two argv elements.
    # shellcheck disable=SC2086
    QSUB_OPTS+=(-pe ${PUBRUN_PE})
fi

# Job body piped to qsub on stdin.
JOB_SCRIPT="$(cat <<'EOF'
#!/bin/bash
set -euo pipefail
PUBRUN_REPO="${PUBRUN_REPO:-}"
PUBRUN_RESULTS_DIR="${PUBRUN_RESULTS_DIR:-}"
PUBRUN_PY="${PUBRUN_PY:-python3}"
PUBRUN_BENCH_ARGS="${PUBRUN_BENCH_ARGS:-}"
PUBRUN_REDACTED_OUT="${PUBRUN_REDACTED_OUT:-}"
PUBRUN_UNREDACTED="${PUBRUN_UNREDACTED:-}"

RESULTS_DIR="${PUBRUN_RESULTS_DIR:-${PWD}/pubrun-bench-results}"
case "$RESULTS_DIR" in
    /*) ;;
    *)  RESULTS_DIR="${PWD}/${RESULTS_DIR}" ;;
esac
mkdir -p "$RESULTS_DIR"

NODE="$(hostname)"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
ANON_ID="$(printf '%s' "$NODE" | "$PUBRUN_PY" -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest()[:8])' 2>/dev/null || echo 'node')"
[ -n "$ANON_ID" ] || ANON_ID="node"
REDACTED_OUT="${PUBRUN_REDACTED_OUT:-$RESULTS_DIR/pubrun-bench-${ANON_ID}-${STAMP}.redacted.json}"
UNREDACTED_OUT="$RESULTS_DIR/${NODE}-${STAMP}.unredacted.json"

if ! "$PUBRUN_PY" -c "import pubrun.minimal, pubrun._bench.harness" 2>/dev/null; then
    if [ -n "$PUBRUN_REPO" ] && [ -d "$PUBRUN_REPO/src" ]; then
        export PYTHONPATH="$PUBRUN_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
        "$PUBRUN_PY" -c "import pubrun.minimal, pubrun._bench.harness" 2>/dev/null || {
            echo "ERROR: 'pubrun._bench.harness' is not importable with $PUBRUN_PY (even with $PUBRUN_REPO/src on PYTHONPATH); run '$PUBRUN_PY -m pip install pubrun' (or '-e $PUBRUN_REPO')." >&2
            exit 1
        }
    else
        echo "ERROR: 'pubrun._bench.harness' is not importable with $PUBRUN_PY; run '$PUBRUN_PY -m pip install pubrun'." >&2
        exit 1
    fi
fi

HARNESS_OUT_ARGS=(--redacted-out "$REDACTED_OUT")
if [ -n "$PUBRUN_UNREDACTED" ]; then
    HARNESS_OUT_ARGS+=(--out "$UNREDACTED_OUT")
fi
# shellcheck disable=SC2086
"$PUBRUN_PY" -m pubrun._bench.harness "${HARNESS_OUT_ARGS[@]}" $PUBRUN_BENCH_ARGS
echo "Done. Redacted result: $REDACTED_OUT"
EOF
)"

echo "Submitting pubrun benchmark to SGE (default placement)..."
printf '%s\n' "$JOB_SCRIPT" | qsub "${QSUB_OPTS[@]}"
