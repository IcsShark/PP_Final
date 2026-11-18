#!/usr/bin/env bash
# E4 step 1: rebuild GRAPH exactly as E0-E2 did, check it is byte-identical to
# the reference CSR, and convert the same edges to a GAPBS .wsg.
#
# Usage (one compute job per graph; run -c 12 so the node's RAM is ours):
#   run -c 12 -- bash scripts/exp/e4_prep.sh GRAPH
#
#   raw .gz / bin/gen --emit-wel --> tmp/GRAPH.csr + tmp/GRAPH.wel
#   cmp tmp/GRAPH.csr $E4_REF_CSR/GRAPH.csr             (same graph + weights)
#   GAPBS converter -f tmp/GRAPH.wel -w -b $E4_OUT/GRAPH.wsg
#
# The regenerated .csr and the .wel only live in node-local tmp (deleted when
# the job ends): the home quota (10 GB) cannot hold them. Only the .wsg is
# kept, and e4_all.sh deletes it once the graph's runs are done.
# `run` always exits 0, so the result is written to $E4_RES/status/prep_GRAPH.
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"

G="${1:?usage: e4_prep.sh GRAPH}"
mkdir -p "$E4_OUT" "$E4_RES/logs" "$E4_RES/status"
LOG="$E4_RES/logs/prep_$G.log"
STATUS="$E4_RES/status/prep_$G"
exec > >(tee "$LOG") 2>&1
echo "FAIL (incomplete)" > "$STATUS"

TMP="$(e4_mktmp)"
trap 'rm -rf "$TMP"' EXIT
echo "== prep $G on $(hostname) at $(date -Is), tmp=$TMP"
SECONDS=0

CSR="$TMP/$G.csr"
WEL="$TMP/$G.wel"
WSG="$E4_OUT/$G.wsg"

# Exactly the arguments of scripts/convert-all.sh and scripts/gen-synthetic.sh.
RW=(--rand-weights 1,262144 --seed 1)
conv() { # gz-file extra-convert-flags...
  local gz=$1; shift
  local txt="$TMP/$G.txt"
  gzip -dc "$E4_RAW/$gz" > "$txt"
  "$E4_REPO/bin/convert" "$txt" -o "$CSR" "$@" --emit-wel "$WEL"
  rm -f "$txt"
}
build() {
case "$G" in
  NY)       conv dimacs9_USA-road-d.NY.gr.gz  --format dimacs ;;
  CTR)      conv dimacs9_USA-road-d.CTR.gr.gz --format dimacs ;;
  USA)      conv dimacs9_USA-road-d.USA.gr.gz --format dimacs ;;
  LJ)       conv snap_soc-LiveJournal1.txt.gz "${RW[@]}" ;;
  OK)       conv snap_com-orkut.ungraph.txt.gz --one-indexed --symmetrize "${RW[@]}" ;;
  kron23)   "$E4_REPO/bin/gen" kron  --scale 23 --degree 16 --seed 1 -o "$CSR" --emit-wel "$WEL" ;;
  urand23)  "$E4_REPO/bin/gen" urand --scale 23 --degree 16 --seed 1 -o "$CSR" --emit-wel "$WEL" ;;
  grid2896) "$E4_REPO/bin/gen" grid  --side 2896            --seed 1 -o "$CSR" --emit-wel "$WEL" ;;
  *) e4_die "unknown graph $G" ;;
esac
}
build | tee "$TMP/ours.out"
read -r ON OM < <(grep -oE 'n=[0-9]+ m=[0-9]+' "$TMP/ours.out" | tail -1 | sed 's/n=\([0-9]*\) m=\([0-9]*\)/\1 \2/')
[ -n "${OM:-}" ] || e4_die "cannot parse n/m from our tool output"
echo "-- csr+wel done (${SECONDS}s); wel size $(stat -c %s "$WEL") bytes"

cmp "$CSR" "$E4_REF_CSR/$G.csr" || e4_die "$CSR differs from $E4_REF_CSR/$G.csr"
echo "-- cmp OK: $CSR == $E4_REF_CSR/$G.csr"

M_WEL=$(wc -l < "$WEL")
[ "$M_WEL" = "$OM" ] || e4_die ".wel has $M_WEL edges but our CSR has m=$OM"
# -w: keep weights (without it GAPBS drops them). No -s: keep edges directed
# exactly as in our CSR (LJ is directed; the others are already symmetric).
rm -f "$CSR"
"$GAPBS_DIR/converter" -f "$WEL" -w -b "$WSG.part" | tee "$TMP/conv.out"
rm -f "$WEL"
# GAPBS's writer does not check write errors (e.g. quota): verify the size.
# Layout: directed flag (1) + m (8) + n (8) + 2 x [(n+1) offsets + m edges] x 8.
WANT=$((17 + 2 * ((ON + 1) * 8 + OM * 8)))
HAVE=$(stat -c %s "$WSG.part")
[ "$HAVE" = "$WANT" ] || e4_die "$WSG.part has $HAVE bytes, expected $WANT (disk quota?)"
mv "$WSG.part" "$WSG"
echo "-- wsg done (${SECONDS}s); size $HAVE bytes (as expected)"

read -r GN GM < <(sed -n 's/^Graph has \([0-9]*\) nodes and \([0-9]*\) directed edges.*/\1 \2/p' "$TMP/conv.out")
[ -n "${GN:-}" ] || e4_die "cannot parse GAPBS graph stats (expected a directed graph)"
[ "$GN" = "$ON" ] && [ "$GM" = "$OM" ] || e4_die "GAPBS n=$GN m=$GM, ours n=$ON m=$OM"
echo "-- GAPBS graph: n=$GN m=$GM (same as ours)"
echo "OK n=$GN m=$GM" > "$STATUS"
echo "== prep $G OK in ${SECONDS}s"
