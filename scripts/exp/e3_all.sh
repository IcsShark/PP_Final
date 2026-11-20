#!/usr/bin/env bash
# Run the whole E3 experiment from the LOGIN node. Each step is its own Slurm
# job via `run -c 12` (QoS: one job at a time, <= 30 min each); every step is
# resumable, so if a job hits its time limit just run this script again.
#
#   module load pp && bash scripts/exp/e3_all.sh
set -u
cd "$(dirname "$0")/../.."
LIMIT=1680   # seconds; stay below the 30-minute job limit

step() { echo; echo "######## $*"; "$@" || { echo "step failed: $*"; exit 1; }; }

step run -c 4 -- make -j4
step run -c 12 -- make test
step run -c 12 -- timeout $LIMIT bash scripts/exp/e3_check_fields.sh
step run -c 12 -- timeout $LIMIT bash scripts/exp/e3_select_delta.sh
# timing and stats may need more than one job each; repeat until all markers exist
for kind in timing stats; do
  for attempt in 1 2 3; do
    n=$(ls results/e3_imbalance/.done/${kind}_* 2>/dev/null | wc -l)
    [ "$n" -ge 20 ] && break
    run -c 12 -- timeout $LIMIT bash scripts/exp/e3_run_$kind.sh
    [ -f results/e3_imbalance/FAILED ] && { echo "verification failed, see results/e3_imbalance/FAILED"; exit 1; }
  done
done
step run -c 12 -- timeout $LIMIT python3 scripts/exp/e3_hub_degrees.py
step bash scripts/exp/e3_meta.sh
echo; echo "E3 runs complete. Next: python3 analysis/e3_imbalance.py (needs numpy/pandas/matplotlib)."
