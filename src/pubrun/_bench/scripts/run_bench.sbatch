#!/bin/bash
# pubrun benchmark harness -- Slurm batch job (packaged canonical script).
#
# Runs `python -m pubrun._bench.harness` on one compute node and writes a
# node-tagged redacted result JSON to a persistent writable results directory
# (not $TMPDIR, which is purged on job end).
#
# Submit via `pubrun bench` or `submit_bench.sh` (which picks a random idle CPU
# node), or directly with: sbatch <path/to/run_bench.sbatch>
#
# Cluster-specific settings (partition/account) are read from the environment
# so this file need not be edited.
#
#SBATCH --job-name=pubrun-bench
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=pubrun-bench-%N-%j.out

set -euo pipefail

# --- Configuration (override via environment) --------------------------------
PUBRUN_REPO="${PUBRUN_REPO:-}"
PUBRUN_RESULTS_DIR="${PUBRUN_RESULTS_DIR:-}"
PUBRUN_PY="${PUBRUN_PY:-python3}"
PUBRUN_BENCH_ARGS="${PUBRUN_BENCH_ARGS:-}"
PUBRUN_REDACTED_OUT="${PUBRUN_REDACTED_OUT:-}"
PUBRUN_UNREDACTED="${PUBRUN_UNREDACTED:-}"

# Resolve a writable, unambiguous absolute results directory without requiring
# a source checkout.
if [ -n "$PUBRUN_RESULTS_DIR" ]; then
    RESULTS_DIR="$PUBRUN_RESULTS_DIR"
elif [ -n "$PUBRUN_REPO" ] && [ -d "$PUBRUN_REPO/benchmarks" ]; then
    RESULTS_DIR="$PUBRUN_REPO/benchmarks/results"
else
    RESULTS_DIR="${PWD}/pubrun-bench-results"
fi
case "$RESULTS_DIR" in
    /*) ;;
    *)  RESULTS_DIR="${PWD}/${RESULTS_DIR}" ;;
esac
mkdir -p "$RESULTS_DIR"

NODE="${SLURMD_NODENAME:-$(hostname)}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
# Derive an opaque short hash for the default share-safe filename so raw cluster
# node names do not leak via the filename itself.
ANON_ID="$(printf '%s' "$NODE" | "$PUBRUN_PY" -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest()[:8])' 2>/dev/null || echo 'node')"
[ -n "$ANON_ID" ] || ANON_ID="node"
# Redacted-only by default (matches `pubrun bench`): always write a share-safe
# redacted file; write the identifying unredacted copy only when
# PUBRUN_UNREDACTED is set. A caller (`pubrun bench` submit-and-wait) may pin
# PUBRUN_REDACTED_OUT so it can find the result deterministically.
REDACTED_OUT="${PUBRUN_REDACTED_OUT:-$RESULTS_DIR/pubrun-bench-${ANON_ID}-${STAMP}.redacted.json}"
UNREDACTED_OUT="$RESULTS_DIR/${NODE}-${STAMP}.unredacted.json"

echo "=== pubrun benchmark ==="
echo "node          : $NODE"
if [ -n "$PUBRUN_REPO" ]; then
    echo "repo          : $PUBRUN_REPO"
fi
echo "results dir   : $RESULTS_DIR"
echo "python        : $PUBRUN_PY"
echo "harness args  : ${PUBRUN_BENCH_ARGS:-<full run>}"
echo "redacted out  : $REDACTED_OUT"
if [ -n "$PUBRUN_UNREDACTED" ]; then
    echo "unredacted out: $UNREDACTED_OUT"
fi

# Fail early with a clear message if pubrun._bench.harness is not importable on
# this node. Import pubrun.minimal first so `-c` never triggers pubrun auto-start.
if ! "$PUBRUN_PY" -c "import pubrun.minimal, pubrun._bench.harness" 2>/dev/null; then
    if [ -n "$PUBRUN_REPO" ] && [ -d "$PUBRUN_REPO/src" ]; then
        export PYTHONPATH="$PUBRUN_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
        if ! "$PUBRUN_PY" -c "import pubrun.minimal, pubrun._bench.harness" 2>/dev/null; then
            echo "ERROR: 'pubrun._bench.harness' is not importable with $PUBRUN_PY (even with $PUBRUN_REPO/src on PYTHONPATH)." >&2
            echo "       Install pubrun on this node: '$PUBRUN_PY -m pip install pubrun' (or '-e $PUBRUN_REPO')." >&2
            exit 1
        fi
    else
        echo "ERROR: 'pubrun._bench.harness' is not importable with $PUBRUN_PY." >&2
        echo "       Install pubrun on this node: '$PUBRUN_PY -m pip install pubrun'." >&2
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
