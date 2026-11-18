#!/usr/bin/env bash
# E4 diagnostic: rebuild each GRAPH in node-local tmp with the exact
# convert-all.sh / gen-synthetic.sh arguments and compare it with the shared
# reference CSR; on a mismatch, e4_csrdiff shows where and whether either file
# is an invalid build_csr output. This is how the bad reference LJ.csr was found.
#
# Usage: run -c 12 -- bash scripts/exp/e4_check_ref.sh [GRAPH...]
# Output: $E4_RES/ref_check.log
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"

mkdir -p "$E4_RES"
exec > >(tee "$E4_RES/ref_check.log") 2>&1
TMP="$(e4_mktmp)"
trap 'rm -rf "$TMP"' EXIT
echo "== check_ref on $(hostname) at $(date -Is)"
SECONDS=0

# Links against the library objects of the normal build (make first).
g++ -O2 -std=c++20 -fopenmp -I"$E4_REPO/include" "$E4_REPO/scripts/exp/e4_csrdiff.cpp" \
  "$E4_REPO/build/normal/src/graph.o" -o "$TMP/e4_csrdiff"

graphs=("$@")
[ ${#graphs[@]} -gt 0 ] || graphs=("${E4_GRAPHS[@]}")
B="$E4_REPO/bin"
RW=(--rand-weights 1,262144 --seed 1)
for G in "${graphs[@]}"; do
  echo "===== $G"
  C="$TMP/$G.csr"
  case "$G" in
    NY|CTR|USA)
      gzip -dc "$E4_RAW/dimacs9_USA-road-d.$G.gr.gz" > "$TMP/x.txt"
      "$B/convert" "$TMP/x.txt" -o "$C" --format dimacs > /dev/null ;;
    LJ)
      gzip -dc "$E4_RAW/snap_soc-LiveJournal1.txt.gz" > "$TMP/x.txt"
      "$B/convert" "$TMP/x.txt" -o "$C" "${RW[@]}" > /dev/null ;;
    OK)
      gzip -dc "$E4_RAW/snap_com-orkut.ungraph.txt.gz" > "$TMP/x.txt"
      "$B/convert" "$TMP/x.txt" -o "$C" --one-indexed --symmetrize "${RW[@]}" > /dev/null ;;
    kron23)   "$B/gen" kron  --scale 23 --degree 16 --seed 1 -o "$C" > /dev/null ;;
    urand23)  "$B/gen" urand --scale 23 --degree 16 --seed 1 -o "$C" > /dev/null ;;
    grid2896) "$B/gen" grid  --side 2896            --seed 1 -o "$C" > /dev/null ;;
    *) e4_die "unknown graph $G" ;;
  esac
  rm -f "$TMP/x.txt"
  if cmp -s "$C" "$E4_REF_CSR/$G.csr"; then
    echo "identical to $E4_REF_CSR/$G.csr"
  else
    echo "DIFFERENT from $E4_REF_CSR/$G.csr  (A = rebuilt, B = reference)"
    "$TMP/e4_csrdiff" "$C" "$E4_REF_CSR/$G.csr" || true
  fi
  rm -f "$C"
done
echo "== check_ref OK in ${SECONDS}s"
