#!/usr/bin/env bash
# E4 extra: GAPBS iteration count (sssp -l prints "took N iterations") at the
# graph's best Delta, t=12, first source, to compare with our phase count
# (`phases` column of the ours CSV). Not a timing run: -l adds logging.
#
# Usage: run -c 12 -- bash scripts/exp/e4_iters.sh GRAPH   (after its runs)
# Output: $E4_RES/iters/GRAPH.csv  graph,delta,threads,source,gapbs_iterations,ours_phases
{ # read the whole script first: replacing this file mid-run is then safe
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"

G="${1:?usage: e4_iters.sh GRAPH}"
mkdir -p "$E4_RES/iters" "$E4_RES/logs" "$E4_RES/status"
LOG="$E4_RES/logs/iters_$G.log"
STATUS="$E4_RES/status/iters_$G"
CSV="$E4_RES/iters/$G.csv"
exec > >(tee "$LOG") 2>&1
echo "FAIL (incomplete)" > "$STATUS"
echo "== iters $G on $(hostname) at $(date -Is)"
SECONDS=0

BEST=$(awk -F, -v g="$G" '$1 == g { print $2 }' "$E4_RES/deltas.csv")
[ -n "$BEST" ] || e4_die "no best delta for $G"
f="$E4_RES/raw/${G}_t12_d${BEST}.ours.csv"
[ -s "$f" ] || e4_die "no ours run $f"
# first row: source and our phase count (identical across reps)
read -r S PH < <(awk -F, 'NR == 2 { print $8, $11 }' "$f")
IT=$(OMP_NUM_THREADS=12 "$GAPBS_DIR/sssp" -f "$E4_OUT/$G.wsg" -d "$BEST" -r "$S" -n 1 -l \
      | sed -n 's/^took \([0-9]*\) iterations/\1/p')
[ -n "$IT" ] || e4_die "no iteration count for $G"
{ echo "graph,delta,threads,source,gapbs_iterations,ours_phases"; echo "$G,$BEST,12,$S,$IT,$PH"; } > "$CSV"
cat "$CSV"
[ "$(wc -l < "$CSV")" = 2 ] || e4_die "$CSV incomplete"
echo "OK" > "$STATUS"
echo "== iters $G OK in ${SECONDS}s"
exit
}
