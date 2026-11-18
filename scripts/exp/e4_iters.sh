#!/usr/bin/env bash
# E4 extra: GAPBS iteration count (sssp -l prints "took N iterations") at each
# graph's best Delta, t=12, first source, to compare with our phase count
# (`phases` column of the ours CSV). Not a timing run: -l adds logging.
#
# Usage: run -c 12 -- bash scripts/exp/e4_iters.sh [GRAPH...]   (after e4_all.sh)
# Output: $E4_RES/iters.csv  graph,delta,threads,source,gapbs_iterations
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"

mkdir -p "$E4_RES/logs" "$E4_RES/status"
LOG="$E4_RES/logs/iters.log"
STATUS="$E4_RES/status/iters"
CSV="$E4_RES/iters.csv"
exec > >(tee "$LOG") 2>&1
echo "FAIL (incomplete)" > "$STATUS"
echo "== iters on $(hostname) at $(date -Is)"
SECONDS=0

graphs=("$@")
[ ${#graphs[@]} -gt 0 ] || graphs=("${E4_GRAPHS[@]}")
echo "graph,delta,threads,source,gapbs_iterations" > "$CSV"
for G in "${graphs[@]}"; do
  BEST=$(awk -F, -v g="$G" '$1 == g { print $2 }' "$E4_RES/deltas.csv")
  [ -n "$BEST" ] || { echo "skip $G (no best delta)"; continue; }
  f="$E4_RES/raw/${G}_t12_d${BEST}.ours.csv"
  [ -s "$f" ] || { echo "skip $G (no ours run)"; continue; }
  S=$(awk -F, 'NR == 2 { print $8 }' "$f")
  it=$(OMP_NUM_THREADS=12 "$GAPBS_DIR/sssp" -f "$E4_OUT/$G.wsg" -d "$BEST" -r "$S" -n 1 -l \
        | sed -n 's/^took \([0-9]*\) iterations/\1/p')
  [ -n "$it" ] || e4_die "no iteration count for $G"
  echo "$G,$BEST,12,$S,$it" | tee -a "$CSV"
done
echo "OK" > "$STATUS"
echo "== iters OK in ${SECONDS}s"
