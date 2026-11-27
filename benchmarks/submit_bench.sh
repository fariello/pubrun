#!/bin/bash
# Source-checkout shim for the packaged Slurm benchmark submission script
# (`src/pubrun/_bench/scripts/submit_bench.sh`).
#
# Preserves direct source-checkout invocation (`benchmarks/submit_bench.sh`)
# and defaults PUBRUN_REPO and PUBRUN_RESULTS_DIR to this checkout before
# delegating to the canonical packaged script.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export PUBRUN_REPO="${PUBRUN_REPO:-$(cd "$HERE/.." && pwd)}"
export PUBRUN_RESULTS_DIR="${PUBRUN_RESULTS_DIR:-$PUBRUN_REPO/benchmarks/results}"
exec bash "$PUBRUN_REPO/src/pubrun/_bench/scripts/submit_bench.sh" "$@"
