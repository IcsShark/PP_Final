#!/usr/bin/env bash
# E4 step 2: cheap Delta sweep of our delta-omp, t=12, 1 source, 3 reps
# (spec section 4.4 uses -r 1; NY runs are ~10 ms, so take a median of 3).
#
# Usage: run -c 12 -- bash scripts/exp/e4_sweep.sh GRAPH
# Output: $E4_RES/sweep/GRAPH.csv (bin/sssp CSV), status in $E4_RES/status/sweep_GRAPH
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"

G="${1:?usage: e4_sweep.sh GRAPH}"
mkdir -p "$E4_RES/sweep" "$E4_RES/logs" "$E4_RES/status"
LOG="$E4_RES/logs/sweep_$G.log"
STATUS="$E4_RES/status/sweep_$G"
CSV="$E4_RES/sweep/$G.csv"
exec > >(tee "$LOG") 2>&1
echo "FAIL (incomplete)" > "$STATUS"
rm -f "$CSV"

echo "== sweep $G on $(hostname) at $(date -Is)"
SECONDS=0
"$E4_REPO/bin/sssp" -g "$E4_REF_CSR/$G.csr" -a delta-omp -d "$E4_SWEEP_DELTAS" -t 12 \
  --sources 1 --seed 42 -r 3 -q --verify --csv "$CSV"
# 13 deltas x 3 reps + header; a short file means a lost write (e.g. quota).
ROWS=$(wc -l < "$CSV")
[ "$ROWS" = $(( $(tr ',' '\n' <<< "$E4_SWEEP_DELTAS" | wc -l) * 3 + 1 )) ] || e4_die "$CSV has $ROWS lines"
echo "OK" > "$STATUS"
echo "== sweep $G OK in ${SECONDS}s"
