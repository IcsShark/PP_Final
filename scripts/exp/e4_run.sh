#!/usr/bin/env bash
# E4 step 3: time ours (delta-omp) and GAPBS sssp on the same graph, sources,
# Delta values and thread count, in the same job (spec section 4.4).
#
# Usage: run -c 12 -- bash scripts/exp/e4_run.sh GRAPH THREADS DELTA[,DELTA...]
#   always -c 12 (whole node) regardless of THREADS.
#
# ours : bin/sssp -a delta-omp --sources 4 --seed 42 -r 3 --verify
#        -> $E4_RES/raw/GRAPH_tT_dTAG.ours.csv     (bin/sssp CSV, one row per rep)
# GAPBS: sssp -f GRAPH.wsg -d D -r SRC -n 3 -v, for the same 4 sources
#        -> $E4_RES/raw/GRAPH_tT_dTAG.gapbs.csv    (one row per trial)
# The .wsg is staged to node-local tmp first (GAPBS reloads it per invocation).
# Any WRONG (ours) or Verification FAIL (GAPBS) stops the script.
{ # read the whole script first: replacing this file mid-run is then safe
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"

G="${1:?usage: e4_run.sh GRAPH THREADS DELTAS}"
T="${2:?threads}"
DELTAS="${3:?deltas}"
TAG="${G}_t${T}_d${DELTAS//,/-}"
mkdir -p "$E4_RES/raw" "$E4_RES/logs" "$E4_RES/status"
LOG="$E4_RES/logs/run_$TAG.log"
STATUS="$E4_RES/status/run_$TAG"
OURS="$E4_RES/raw/$TAG.ours.csv"
GAP="$E4_RES/raw/$TAG.gapbs.csv"
exec > >(tee "$LOG") 2>&1
echo "FAIL (incomplete)" > "$STATUS"
rm -f "$OURS" "$GAP"

TMP="$(e4_mktmp)"
trap 'rm -rf "$TMP"' EXIT
HOST="$(hostname -s)"
echo "== run $TAG on $HOST at $(date -Is), SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-?}"
SECONDS=0

# ---- ours
echo "csr: $(e4_csr "$G")"
"$E4_REPO/bin/sssp" -g "$(e4_csr "$G")" -a delta-omp -d "$DELTAS" -t "$T" \
  --sources 4 --seed 42 -r 3 --verify --csv "$OURS" | tee "$TMP/ours.out"
SOURCES=$(sed -n 's/^sources: *//p' "$TMP/ours.out")
[ -n "$SOURCES" ] || e4_die "no sources line in bin/sssp output"
echo "-- ours done (${SECONDS}s), sources: $SOURCES"

# ---- GAPBS
cp "$E4_OUT/$G.wsg" "$TMP/$G.wsg"
echo "graph,impl,threads,delta,source,trial,time_ms,verified,host" > "$GAP"
fails=0
for D in ${DELTAS//,/ }; do
  for S in $SOURCES; do
    echo "-- gapbs d=$D t=$T src=$S"
    rc=0
    OMP_NUM_THREADS=$T "$GAPBS_DIR/sssp" -f "$TMP/$G.wsg" -d "$D" -r "$S" -n 3 -v > "$TMP/g.out" || rc=$?
    cat "$TMP/g.out"
    [ "$rc" = 0 ] || e4_die "GAPBS sssp exited with $rc"
    awk -v g="$G" -v t="$T" -v d="$D" -v s="$S" -v h="$HOST" '
      /^Trial Time:/   { n++; tm[n] = $3 * 1000 }
      /^Verification:/ { v[n] = ($2 == "PASS") ? 1 : 0 }
      END { for (i = 1; i <= n; i++)
              printf "%s,gapbs,%s,%s,%s,%d,%.4f,%d,%s\n", g, t, d, s, i - 1, tm[i], (i in v) ? v[i] : -1, h }
    ' "$TMP/g.out" >> "$GAP"
    ntrial=$(grep -c '^Trial Time:' "$TMP/g.out" || true)
    npass=$(grep -cE '^Verification: +PASS' "$TMP/g.out" || true)
    [ "$ntrial" = 3 ] && [ "$npass" = 3 ] || { fails=1; echo "!! GAPBS verification: $npass/$ntrial PASS"; break 2; }
  done
done
[ "$fails" = 0 ] || e4_die "GAPBS verification failed for $TAG (see $LOG)"
# 4 sources x 3 reps x (#deltas) rows + header in each CSV; catches lost writes.
WANT=$(( 4 * 3 * $(tr ',' '\n' <<< "$DELTAS" | wc -l) + 1 ))
for f in "$OURS" "$GAP"; do
  [ "$(wc -l < "$f")" = "$WANT" ] || e4_die "$f has $(wc -l < "$f") lines, expected $WANT"
done
echo "OK $(date -Is) ${SECONDS}s" > "$STATUS"
echo "== run $TAG OK in ${SECONDS}s"
exit
}
