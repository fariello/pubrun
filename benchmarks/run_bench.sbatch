#!/bin/bash
# pubrun benchmark harness — Slurm batch job.
#
# Runs benchmarks/harness.py on ONE node and writes a node-tagged result JSON to
# benchmarks/results/ (persistent — NOT $TMPDIR, which is purged on job end).
#
# Submit via benchmarks/submit_bench.sh (which picks a random idle CPU node), or
# directly with:  sbatch benchmarks/run_bench.sbatch
#
# Cluster-specific settings (partition/account) are read from the environment so
# this file need not be edited; submit_bench.sh sets them, or export them
# yourself. See the "# EDIT" defaults below.
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
# Repo root: default to the repo containing this script.
PUBRUN_REPO="${PUBRUN_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)}"
# Python interpreter with pubrun importable (editable install or installed).
PUBRUN_PY="${PUBRUN_PY:-python3}"     # EDIT default if you use a venv, e.g. $HOME/venv/p3.14/bin/python
# Extra harness args (e.g. "--quick" or "--passes 3"); empty = full run.
PUBRUN_BENCH_ARGS="${PUBRUN_BENCH_ARGS:-}"

cd "$PUBRUN_REPO"

RESULTS_DIR="$PUBRUN_REPO/benchmarks/results"
mkdir -p "$RESULTS_DIR"

NODE="${SLURMD_NODENAME:-$(hostname)}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT="$RESULTS_DIR/${NODE}-${STAMP}.json"

echo "=== pubrun benchmark ==="
echo "node        : $NODE"
echo "repo        : $PUBRUN_REPO"
echo "python      : $PUBRUN_PY"
echo "harness args: ${PUBRUN_BENCH_ARGS:-<full run>}"
echo "output      : $OUT"

# Fail early with a clear message if pubrun isn't importable on this node.
if ! "$PUBRUN_PY" -c "import pubrun" 2>/dev/null; then
    # Try the repo's src/ (editable-style) before giving up.
    export PYTHONPATH="$PUBRUN_REPO/src${PYTHONPATH:+:$PYTHONPATH}"
    if ! "$PUBRUN_PY" -c "import pubrun" 2>/dev/null; then
        echo "ERROR: 'pubrun' is not importable with $PUBRUN_PY (even with src/ on PYTHONPATH)." >&2
        echo "       Install it on this node: '$PUBRUN_PY -m pip install -e $PUBRUN_REPO'." >&2
        exit 1
    fi
fi

# shellcheck disable=SC2086
"$PUBRUN_PY" benchmarks/harness.py --out "$OUT" $PUBRUN_BENCH_ARGS

echo "Done. Result: $OUT"
