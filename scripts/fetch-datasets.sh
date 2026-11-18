#!/usr/bin/env bash
# Download the raw datasets listed in datasets/SOURCES.md and verify md5.
#
# Usage: bash scripts/fetch-datasets.sh [DATA_DIR]
#   DATA_DIR: data root; files go to DATA_DIR/raw/
#             default: $PP_DATA_DIR, else <repo>/datasets (gitignored)
# Run on the login node (compute nodes usually have no outbound network).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${1:-${PP_DATA_DIR:-$REPO/datasets}}"
RAW="$DATA/raw"
mkdir -p "$RAW"; cd "$RAW"
WB="https://web.archive.org/web/2020id_/http://www.dis.uniroma1.it/challenge9/data/USA-road-d"

get() { # name url
  if [ -s "$1" ]; then echo "skip $1"; return 0; fi
  echo "fetch $1"
  curl -fSL --retry 5 --retry-delay 5 -C - -o "$1.part" "$2" && mv "$1.part" "$1"
}

# Wayback: one at a time (archive.org throttles parallel requests per IP)
road() {
  get dimacs9_USA-road-d.NY.gr.gz  "$WB/USA-road-d.NY.gr.gz"
  get dimacs9_USA-road-d.CTR.gr.gz "$WB/USA-road-d.CTR.gr.gz"
  get dimacs9_USA-road-d.USA.gr.gz "$WB/USA-road-d.USA.gr.gz"
}

pids=()
road & pids+=($!)
get snap_soc-LiveJournal1.txt.gz  "https://snap.stanford.edu/data/soc-LiveJournal1.txt.gz" & pids+=($!)
get snap_com-orkut.ungraph.txt.gz "https://snap.stanford.edu/data/bigdata/communities/com-orkut.ungraph.txt.gz" & pids+=($!)

fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done
[ "$fail" -eq 0 ] || { echo "some downloads failed; rerun to resume" >&2; exit 1; }

md5sum -c "$REPO/datasets/md5sums.txt"
echo "raw datasets in $RAW"
