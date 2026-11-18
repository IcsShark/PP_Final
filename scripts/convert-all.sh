#!/usr/bin/env bash
# Convert the raw datasets (see datasets/SOURCES.md) to binary CSR.
#
# Usage: bash scripts/convert-all.sh [DATA_DIR] [--wel]
#   DATA_DIR: data root; reads DATA_DIR/raw/*.gz, writes DATA_DIR/csr/*.csr
#             default: $PP_DATA_DIR, else <repo>/datasets (gitignored)
#   --wel:    also write GAPBS .wel text (large; only needed for the GAPBS baseline)
# Builds bin/convert itself if needed (-march=native: run it on a compute node).
# On the cluster: module load pp && run -c 1 -- bash scripts/convert-all.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
WEL=""
args=()
for a in "$@"; do
  if [ "$a" = "--wel" ]; then WEL=1; else args+=("$a"); fi
done
DATA="${args[0]:-${PP_DATA_DIR:-$REPO/datasets}}"
RAW="$DATA/raw"
OUT="$DATA/csr"
CONVERT="$REPO/bin/convert"
make -C "$REPO" bin/convert   # no-op if up to date; runs on whatever node runs this script
mkdir -p "$OUT"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/pp_convert.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# Same weight range as Dong et al. SPAA'21 for the unweighted graphs; fixed
# seed so everyone builds byte-identical graphs.
RW=(--rand-weights 1,262144 --seed 1)

conv() { # name gz-file extra-convert-flags...
  local name=$1 gz=$2; shift 2
  if [ -s "$OUT/$name.csr" ]; then echo "skip $name (exists)"; return 0; fi
  echo "== $name"
  local txt="$TMP/$name.txt"
  gzip -dc "$RAW/$gz" > "$txt"
  local wel=()
  [ -n "$WEL" ] && wel=(--emit-wel "$OUT/$name.wel")
  "$CONVERT" "$txt" -o "$OUT/$name.csr" "$@" "${wel[@]}"
  rm -f "$txt"
}

# Road: DIMACS distance weights; parallel arcs collapse to the min weight.
conv NY  dimacs9_USA-road-d.NY.gr.gz  --format dimacs
conv CTR dimacs9_USA-road-d.CTR.gr.gz --format dimacs
conv USA dimacs9_USA-road-d.USA.gr.gz --format dimacs

# LiveJournal: directed, 0-indexed; self-loops are dropped by default.
# Expect m = 68,993,773 - 518,382 = 68,475,391.
conv LJ snap_soc-LiveJournal1.txt.gz "${RW[@]}"

# Orkut: each undirected pair stored once -> symmetrize (both directions get
# the same weight). 1-indexed with gaps (ids 1..3,072,626, 3,072,441 used), so
# the CSR has 185 isolated vertices; not remapped. Expect m = 234,370,166.
conv OK snap_com-orkut.ungraph.txt.gz --one-indexed --symmetrize "${RW[@]}"

echo "CSR files in $OUT"
ls -l "$OUT"
