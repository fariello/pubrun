#!/bin/bash
# Submit the pubrun benchmark job (run_bench.sbatch) to a RANDOM idle CPU node.
#
# Usage:
#   benchmarks/submit_bench.sh                 # random idle node, full run
#   benchmarks/submit_bench.sh --quick         # pass args through to the harness
#   PUBRUN_PARTITION=compute benchmarks/submit_bench.sh
#
# Configuration (environment variables; all optional):
#   PUBRUN_PARTITION   Slurm partition to draw idle nodes from and submit to.
#                      If unset, uses the cluster default partition.
#   PUBRUN_PY          Python with pubrun importable (default: python3).
#   PUBRUN_REPO        Repo root (default: the repo containing this script).
#   PUBRUN_EXCLUDE     Regex of node names to exclude (e.g. GPU nodes), optional.
#
# Any extra CLI args are forwarded to harness.py via PUBRUN_BENCH_ARGS.
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

# Collect idle node names (one per line, deduped).
mapfile -t IDLE_NODES < <(sinfo "${SINFO_ARGS[@]}" 2>/dev/null | sort -u | sed '/^$/d')

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
# Pass through repo/python so the job doesn't have to guess.
export PUBRUN_REPO="${PUBRUN_REPO:-$(cd "$HERE/.." && pwd)}"
export PUBRUN_PY="${PUBRUN_PY:-python3}"
# Optional deterministic output paths (set by `pubrun bench` submit-and-wait so the login
# node can find the redacted result). PUBRUN_UNREDACTED=1 also writes the identifying copy.
export PUBRUN_REDACTED_OUT="${PUBRUN_REDACTED_OUT:-}"
export PUBRUN_UNREDACTED="${PUBRUN_UNREDACTED:-}"

# Emit the bare job id on stdout (sbatch --parsable) so a caller can capture it and poll for
# completion. --parsable prints "<jobid>" (or "<jobid>;<cluster>").
SBATCH_OPTS=(--parsable)
[ -n "$PARTITION" ] && SBATCH_OPTS+=(--partition "$PARTITION")

_EXPORT="ALL,PUBRUN_REPO,PUBRUN_PY,PUBRUN_BENCH_ARGS,PUBRUN_REDACTED_OUT,PUBRUN_UNREDACTED"

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
    # No idle node right now — let the scheduler place it whenever one frees up.
    echo "No idle nodes found${PARTITION:+ in partition '$PARTITION'}; submitting" \
         "without pinning (scheduler will place it)." >&2
    sbatch "${SBATCH_OPTS[@]}" \
        --export="$_EXPORT" \
        "$SBATCH_FILE"
fi
