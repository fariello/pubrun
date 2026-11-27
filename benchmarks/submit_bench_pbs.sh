#!/bin/bash
# Source-checkout shim for the packaged PBS / Torque / OpenPBS submission script
# (`src/pubrun/_bench/scripts/submit_bench_pbs.sh`).
#
# STARTING POINT -- adapt to your site. Delegates to the canonical packaged PBS
# script (which builds `qsub` flags via QSUB_OPTS=() argv-array option handling
# and is not validated against a live PBS cluster in CI).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export PUBRUN_REPO="${PUBRUN_REPO:-$(cd "$HERE/.." && pwd)}"
export PUBRUN_RESULTS_DIR="${PUBRUN_RESULTS_DIR:-$PUBRUN_REPO/benchmarks/results}"
exec bash "$PUBRUN_REPO/src/pubrun/_bench/scripts/submit_bench_pbs.sh" "$@"
