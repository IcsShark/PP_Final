#!/usr/bin/env bash
# Write results/e3_imbalance/META.txt (light; may run on the login node).
#   bash scripts/exp/e3_meta.sh
source "$(dirname "$0")/e3_common.sh"

# The E3 code change (section 4) is recorded as a patch against HEAD, so the
# exact code that produced the data is reproducible even before it is committed.
git diff HEAD -- include src tests Makefile > "$OUT/code_change.patch"

{
  echo "E3 load imbalance (Q3a) — metadata"
  echo "generated: $(date '+%F %T %Z')"
  echo
  echo "## Code"
  echo "repo: $(git remote get-url origin 2>/dev/null)"
  echo "branch: $(git branch --show-current)"
  echo "commit (HEAD): $(git rev-parse HEAD)"
  if git diff --quiet HEAD -- include src tests Makefile; then
    echo "working tree: clean (code == HEAD)"
  else
    echo "working tree: HEAD + E3 code change (spec section 4), saved as code_change.patch:"
    git diff --stat HEAD -- include src tests Makefile | sed 's/^/  /'
    echo "  The timing build's machine code is identical to HEAD (checked by objdump);"
    echo "  only the stats build (-DSSSP_STATS) gains max_thread_edges and barrier-wait timing."
  fi
  echo "compiler: $(g++ --version | head -1)"
  echo "build: run -c 4 -- make -j4   (CXXFLAGS -O3 -march=native -std=c++20 -fopenmp)"
  echo
  echo "## Platform"
  echo "every job: run -c 12 (whole node), see hosts.log for per-job hostname and lscpu."
  echo "hosts used: $(grep -o 'on [^ ]*' "$OUT/hosts.log" 2>/dev/null | sort -u | sed 's/on //' | paste -sd' ')"
  echo "CPU: Intel i5-10500, 6 physical cores / 12 hardware threads. The VM's lscpu reports"
  echo "12 cores x 1 thread per core, so which logical CPUs are SMT siblings cannot be"
  echo "controlled or observed. No OMP_PROC_BIND / OMP_PLACES set (OpenMP defaults)."
  echo "OMP env: $(env | grep '^OMP_' | paste -sd' ')"
  echo
  echo "## Data"
  echo "PP_DATA_DIR=$PP_DATA_DIR (read-only)"
  for g in "${GRAPHS[@]}"; do echo "  $CSR/$g.csr  $(stat -c %s "$CSR/$g.csr") bytes"; done
  echo
  echo "## Delta per graph (delta.csv)"
  echo "No E1 results (results/e1_*) on main when E3 ran, so per spec section 5 delta was"
  echo "chosen by a cheap sweep: timing build, -d sweep (2^i * max(w_min,1) up to >= w_max),"
  echo "t=12, sched dynamic,64, --sources 1 --seed 42 -r 1; fastest delta wins (delta_sweep.csv)."
  echo "variant/filter: defaults (all, pop) — E1 had not selected a better combination."
  sed 's/^/  /' "$OUT/delta.csv"
  echo
  echo "## Commands (all from scripts/exp/, see e3_all.sh for the order)"
  echo "  common: graphs=${GRAPHS[*]} scheds=${SCHEDS[*]} threads=$THREADS sources=$SOURCES seed=$SEED"
  echo "  timing: ./bin/sssp -g CSR -a delta-omp -d DELTA -t $THREADS --sched S --sources $SOURCES --seed $SEED -r 3 --verify -q --csv ..."
  echo "  stats : ./bin/sssp_stats -g CSR -a delta-omp -d DELTA -t $THREADS --sched S --sources $SOURCES --seed $SEED -r 1 --verify -q --csv ... --phase-log ..."
  echo "  every run is verified against Dijkstra; verification happens outside the timed region."
  echo
  echo "## Phase logs (not committed)"
  echo "$PLOG/phases_<graph>_<sched>.csv.gz on the workstation ($(hostname -f 2>/dev/null || hostname))"
  du -sh "$PLOG" 2>/dev/null | sed 's/^/  total: /'
  echo
  echo "## Analysis"
  echo "analysis/e3_imbalance.py (numpy/pandas/matplotlib). The cluster's Python has no numpy,"
  echo "so the analysis runs off-cluster on copies of these CSVs and phase logs; plots and"
  echo "tables are copied back into results/e3_imbalance/."
} > "$OUT/META.txt"
echo "wrote $OUT/META.txt"
