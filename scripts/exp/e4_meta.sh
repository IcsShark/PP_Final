#!/usr/bin/env bash
# E4: write $E4_RES/META.txt from the repo, the GAPBS checkout and the job logs.
# Light work; run on the login node after (or during) e4_all.sh.
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"
OUT="$E4_RES/META.txt"

{
echo "# E4 GAPBS baseline - metadata (generated $(date -Is) by scripts/exp/e4_meta.sh)"
echo
echo "## Code"
echo "PP_Final:  $(git -C "$E4_REPO" rev-parse HEAD)  ($(git -C "$E4_REPO" describe --always --dirty), branch $(git -C "$E4_REPO" rev-parse --abbrev-ref HEAD))"
echo "           algorithm code unchanged from main; build: g++ -O3 -march=native -std=c++20 -fopenmp (Makefile)"
echo "GAPBS:     $(git -C "$GAPBS_DIR" rev-parse HEAD)  (https://github.com/sbeamer/gapbs, $(git -C "$GAPBS_DIR" log -1 --format=%cd --date=short))"
echo "           build: its own Makefile, unmodified (g++ -std=c++11 -O3 -Wall -fopenmp; no -march=native),"
echo "           built on a compute node with: run -c 4 -- make -j4"
echo "compiler:  $(g++ --version | head -1)"
echo
echo "## Hosts (compute nodes that ran each step)"
for f in "$E4_RES"/logs/*.log; do
  h=$(sed -n 's/^== .* on \([^ ]*\) at .*/\1/p' "$f" | head -1)
  printf '%-36s %s\n' "$(basename "$f" .log)" "${h%%.*}"
done
echo
echo "## Data"
echo "raw:        $E4_RAW  (downloaded with scripts/fetch-datasets.sh; md5sum -c datasets/md5sums.txt all OK)"
echo "reference:  $E4_REF_CSR  (the CSRs E0-E2 use)"
echo "generated:  $E4_OUT/GRAPH.wsg, deleted once the graph's runs are done (10 GB home quota);"
echo "            the regenerated .csr and the .wel only live in node-local tmp"
echo "check:      e4_prep.sh rebuilds GRAPH.csr with the exact convert-all.sh / gen-synthetic.sh arguments,"
echo "            cmp's it against the reference (must be identical), checks GAPBS reports the same n and m,"
echo "            and checks the .wsg file size against its layout:"
for f in "$E4_RES"/status/prep_*; do [ -f "$f" ] && printf '  %-10s %s\n' "${f##*/prep_}" "$(cat "$f")"; done
echo
echo "## Delta (deltas.csv): best = fastest in the e4_sweep.sh grid (t=12, 1 source, median of 3);"
echo "## runs use the best and its two neighbours. e0_ref_delta is the spec's E0 reference, recorded only."
cat "$E4_RES/deltas.csv" 2>/dev/null || echo "(none yet)"
echo
echo "## Sources (bin/sssp --sources 4 --seed 42; 0-based ids, used verbatim for GAPBS -r)"
for G in "${E4_GRAPHS[@]}"; do
  f=$(ls "$E4_RES"/logs/run_"${G}"_t*.log 2>/dev/null | head -1 || true)
  [ -n "$f" ] && printf '%-10s %s\n' "$G" "$(sed -n 's/^sources: *//p' "$f" | head -1)"
done
echo
echo "## Commands (every timing job: run -c 12, whole node, regardless of threads)"
cat <<'CMDS'
prep : run -c 12 -- bash scripts/exp/e4_prep.sh GRAPH
         gzip -dc raw/X.gz > tmp/X.txt; bin/convert tmp/X.txt -o OUT/X.csr <convert-all.sh args> --emit-wel tmp/X.wel
         (synthetic: bin/gen <gen-synthetic.sh args> -o OUT/X.csr --emit-wel tmp/X.wel)
         cmp OUT/X.csr REF/X.csr
         gapbs/converter -f tmp/X.wel -w -b OUT/X.wsg          (-w keeps weights; no -s, edges stay directed)
sweep: run -c 12 -- bash scripts/exp/e4_sweep.sh GRAPH
         bin/sssp -g REF/X.csr -a delta-omp -d 64,...,262144 -t 12 --sources 1 --seed 42 -r 3 -q --verify --csv sweep/X.csv
run  : run -c 12 -- bash scripts/exp/e4_run.sh GRAPH T DELTA
         bin/sssp -g REF/X.csr -a delta-omp -d DELTA -t T --sources 4 --seed 42 -r 3 --verify --csv raw/X_tT_dD.ours.csv
         for each source S:  OMP_NUM_THREADS=T gapbs/sssp -f tmp/X.wsg -d DELTA -r S -n 3 -v   (.wsg staged to node-local tmp)
driver: nohup bash scripts/exp/e4_all.sh  (login node; submits the jobs above one at a time)
CMDS
echo "OMP environment: only OMP_NUM_THREADS (GAPBS); ours sets threads with -t. No OMP_PROC_BIND/OMP_PLACES."
echo "ours schedule: bin/sssp default (--sched dynamic,64, --variant all, --filter pop)."
echo
echo "## Deviations from docs/E4-experiment-spec.md"
echo "- raw/ read from \$HOME/pp_data/raw (own md5-verified download): the shared raw/ is not readable by this account."
echo "- outputs in \$HOME/pp_data/gapbs instead of the shared \$PP_DATA_DIR/gapbs (user's decision)."
echo "- .wel and the regenerated .csr written to node-local tmp, not to gapbs/; each .wsg deleted after its"
echo "  graph is done. Reason: 10 GB home quota (a USA sweep was lost to 'Disk quota exceeded' and rerun)."
echo "- GAPBS converter needs -w (spec 4.3 omitted it; without it the .wsg would be unweighted)."
echo "- Delta from a sweep for every graph (spec allows it); the E0 references were clearly not optimal on NY t=12."
echo "- sweep uses -r 3 and the median (spec example: -r 1)."
echo "- one job per (graph, threads, Delta) to stay under the 30-min QoS limit."
} > "$OUT"
echo "wrote $OUT"
