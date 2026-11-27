#!/bin/bash
# Source-checkout shim for the packaged Slurm batch script
# (`src/pubrun/_bench/scripts/run_bench.sbatch`).
#
# Retains the #SBATCH directives at the top so `sbatch benchmarks/run_bench.sbatch`
# parses them directly, and resolves the canonical packaged script safely even
# when Slurm copies this file to a spool directory.
#
#SBATCH --job-name=pubrun-bench
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=pubrun-bench-%N-%j.out

set -euo pipefail

PUBRUN_REPO="${PUBRUN_REPO:-}"
PUBRUN_RESULTS_DIR="${PUBRUN_RESULTS_DIR:-}"
PUBRUN_PY="${PUBRUN_PY:-python3}"

if [ -z "$PUBRUN_REPO" ]; then
    _SCRIPT_CANDIDATE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || true)"
    if [ -n "$_SCRIPT_CANDIDATE" ] && [ -f "$_SCRIPT_CANDIDATE/src/pubrun/_bench/scripts/run_bench.sbatch" ]; then
        PUBRUN_REPO="$_SCRIPT_CANDIDATE"
    elif [ -n "${SLURM_SUBMIT_DIR:-}" ] && [ -f "$SLURM_SUBMIT_DIR/src/pubrun/_bench/scripts/run_bench.sbatch" ]; then
        PUBRUN_REPO="$(cd "$SLURM_SUBMIT_DIR" && pwd)"
    elif [ -n "${SLURM_SUBMIT_DIR:-}" ] && [ -f "$SLURM_SUBMIT_DIR/../src/pubrun/_bench/scripts/run_bench.sbatch" ]; then
        PUBRUN_REPO="$(cd "$SLURM_SUBMIT_DIR/.." && pwd)"
    fi
fi

if [ -n "$PUBRUN_REPO" ] && [ -f "$PUBRUN_REPO/src/pubrun/_bench/scripts/run_bench.sbatch" ]; then
    export PUBRUN_REPO
    export PUBRUN_RESULTS_DIR="${PUBRUN_RESULTS_DIR:-$PUBRUN_REPO/benchmarks/results}"
    exec bash "$PUBRUN_REPO/src/pubrun/_bench/scripts/run_bench.sbatch"
fi

PACKAGED_SCRIPT="$("$PUBRUN_PY" -c "import pubrun.minimal, pubrun._bench; print(pubrun._bench.get_submit_script_path('run_bench.sbatch'))" 2>/dev/null || true)"
if [ -n "$PACKAGED_SCRIPT" ] && [ -f "$PACKAGED_SCRIPT" ]; then
    exec bash "$PACKAGED_SCRIPT"
fi

echo "ERROR: could not locate packaged run_bench.sbatch; set PUBRUN_REPO to a pubrun source checkout or ensure pubrun is installed in $PUBRUN_PY." >&2
exit 1
