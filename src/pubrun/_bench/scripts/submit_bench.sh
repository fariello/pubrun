#!/bin/bash
# Submit the pubrun benchmark job (run_bench.sbatch) to a random idle CPU node
# via Slurm (`sbatch`).
#
# Usage:
#   submit_bench.sh                 # random idle node, full run
#   submit_bench.sh --quick         # pass args through to pubrun._bench.harness
#   PUBRUN_PARTITION=compute submit_bench.sh
#
# Configuration (environment variables; all optional):
#   PUBRUN_PARTITION     Slurm partition to draw idle nodes from and submit to.
#                        If unset, uses the cluster default partition.
#   PUBRUN_PY            Python with pubrun importable (default: python3).
#   PUBRUN_REPO          Optional pubrun source checkout root (empty by default).
#   PUBRUN_RESULTS_DIR   Writable directory for benchmark result JSON files.
#   PUBRUN_EXCLUDE       Regex of node names to exclude (e.g. GPU nodes).
#   PUBRUN_REDACTED_OUT  Explicit output path for the share-safe redacted JSON.
#   PUBRUN_UNREDACTED    Non-empty to also write an identifying unredacted copy.
#
# Any extra CLI args are forwarded to `python -m pubrun._bench.harness` via
# PUBRUN_BENCH_ARGS.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SBATCH_FILE="$HERE/run_bench.sbatch"

command -v sinfo  >/dev/null 2>&1 || { echo "ERROR: sinfo not found (is Slurm loaded?)." >&2; exit 1; }
command -v sbatch >/dev/null 2>&1 || { echo "ERROR: sbatch not found (is Slurm loaded?)." >&2; exit 1; }
[ -f "$SBATCH_FILE" ] || { echo "ERROR: $SBATCH_FILE not found." >&2; exit 1; }

PARTITION="${PUBRUN_PARTITION:-}"
EXCLUDE="${PUBRUN_EXCLUDE:-}"

# Build the sinfo query. Restrict to a partition if given.
SINFO_ARGS=(-h -t idle -o "%n")
if [ -n "$PARTITION" ]; then
    SINFO_ARGS+=(-p "$PARTITION")
fi

# Collect idle node names (one per line, deduped; Bash 3.2-compatible).
IDLE_NODES=()
while IFS= read -r _node; do
    [ -n "$_node" ] && IDLE_NODES+=("$_node")
done < <(sinfo "${SINFO_ARGS[@]}" 2>/dev/null | sort -u)

# Optionally drop excluded nodes (e.g. GPU boxes).
if [ -n "$EXCLUDE" ] && [ "${#IDLE_NODES[@]}" -gt 0 ]; then
    FILTERED=()
    for n in "${IDLE_NODES[@]}"; do
        [[ "$n" =~ $EXCLUDE ]] || FILTERED+=("$n")
    done
    IDLE_NODES=("${FILTERED[@]}")
fi

# Args after the script name are forwarded to the harness.
export PUBRUN_BENCH_ARGS="${*:-}"
# Leave PUBRUN_REPO empty unless the caller set it (never point into site-packages).
export PUBRUN_REPO="${PUBRUN_REPO:-}"
export PUBRUN_PY="${PUBRUN_PY:-python3}"

# Resolve and export an absolute writable results directory at submission time.
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

# Optional deterministic output paths (set by `pubrun bench` submit-and-wait so
# the login node can find the redacted result). PUBRUN_UNREDACTED=1 also writes
# the identifying copy.
export PUBRUN_REDACTED_OUT="${PUBRUN_REDACTED_OUT:-}"
export PUBRUN_UNREDACTED="${PUBRUN_UNREDACTED:-}"

# Emit the bare job id on stdout (sbatch --parsable) so a caller can capture it
# and poll for completion. --parsable prints "<jobid>" (or "<jobid>;<cluster>").
SBATCH_OPTS=(--parsable)
if [ -n "$PARTITION" ]; then
    SBATCH_OPTS+=(--partition "$PARTITION")
fi

_EXPORT="ALL,PUBRUN_REPO,PUBRUN_PY,PUBRUN_RESULTS_DIR,PUBRUN_BENCH_ARGS,PUBRUN_REDACTED_OUT,PUBRUN_UNREDACTED"

if [ "${#IDLE_NODES[@]}" -gt 0 ]; then
    # Pick a uniformly random idle node.
    IDX=$(( RANDOM % ${#IDLE_NODES[@]} ))
    TARGET="${IDLE_NODES[$IDX]}"
    echo "Idle nodes (${#IDLE_NODES[@]}): ${IDLE_NODES[*]}" >&2
    echo "Submitting to random idle node: $TARGET" >&2
    sbatch "${SBATCH_OPTS[@]}" --nodelist="$TARGET" \
        --export="$_EXPORT" \
        "$SBATCH_FILE"
else
    # No idle node right now -- let the scheduler place it whenever one frees up.
    echo "No idle nodes found${PARTITION:+ in partition '$PARTITION'}; submitting" \
         "without pinning (scheduler will place it)." >&2
    sbatch "${SBATCH_OPTS[@]}" \
        --export="$_EXPORT" \
        "$SBATCH_FILE"
fi
