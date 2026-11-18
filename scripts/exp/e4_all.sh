#!/usr/bin/env bash
# E4 driver: for each graph, prep -> Delta sweep -> runs at t = 1, 6, 12 ->
# GAPBS iteration count -> delete the graph's .wsg (home quota is 10 GB; set
# E4_KEEP_WSG=1 to keep it).
# Submits one job at a time through `run` (pp_qos: 1 job, <= 30 min each) and
# only waits in between, so it can stay on the login node:
#
#   module load pp
#   nohup bash scripts/exp/e4_all.sh [GRAPH...] > ~/e4_all.log 2>&1 &
#
# Steps whose status file already says OK are skipped, so rerunning resumes.
# Stops at the first failure (verification or otherwise); see results/e4_gapbs/logs.
{ # read the whole script first: replacing this file mid-run is then safe
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"
command -v run > /dev/null || e4_die "'run' not found; module load pp first"
cd "$E4_REPO"


# Never overlap with a job left over from an earlier driver (pp_qos: 1 job).
while [ -n "$(squeue -u "$USER" -h 2>/dev/null)" ]; do sleep 10; done

graphs=("$@")
[ ${#graphs[@]} -gt 0 ] || graphs=("${E4_GRAPHS[@]}")
mkdir -p "$E4_RES"
for G in "${graphs[@]}"; do
  if ok "iters_$G"; then echo "[$(date +%T)] skip $G (done)"; continue; fi
  # .wsg deleted after an earlier, partly finished pass: rebuild it.
  { [ -f "$E4_OUT/$G.wsg" ] && { ! e4_fresh "$G" || [ -f "$E4_OUT/$G.csr" ]; }; } || rm -f "$E4_RES/status/prep_$G"
  job "prep_$G" scripts/exp/e4_prep.sh "$G"
  job "sweep_$G" scripts/exp/e4_sweep.sh "$G"
  NSWEEP=$(( $(tr ',' '\n' <<< "$(e4_sweep_deltas "$G")" | wc -l) * 3 + 1 ))
  wait_lines "$E4_RES/sweep/$G.csv" "$NSWEEP" || e4_die "sweep/$G.csv incomplete on the login node"
  PICK=$(bash scripts/exp/e4_pick_delta.sh "$G") || e4_die "no Delta picked for $G (see message above)"
  IFS=$'\t' read -r DELTAS BEST REF <<< "$PICK"
  echo "[$(date +%T)] $G deltas=$DELTAS best=$BEST (E0 ref $REF)"
  # deltas.csv: one line per graph (latest wins)
  DC="$E4_RES/deltas.csv"
  { echo "graph,best_delta,deltas,e0_ref_delta"
    { [ -f "$DC" ] && grep -v -e '^graph,' -e "^$G," "$DC" || true
      echo "$G,$BEST,${DELTAS//,/ },$REF"; } | sort
  } > "$DC.new" && mv "$DC.new" "$DC"
  # One job per (graph, threads, Delta): with GAPBS verifying every trial
  # (serial Dijkstra), a whole (graph, threads) block can exceed 30 min on OK.
  for T in "${E4_THREADS[@]}"; do
    for D in ${DELTAS//,/ }; do
      job "run_${G}_t${T}_d${D}" scripts/exp/e4_run.sh "$G" "$T" "$D"
    done
  done
  job "iters_$G" scripts/exp/e4_iters.sh "$G"
  if [ "${E4_KEEP_WSG:-0}" != 1 ]; then
    rm -f "$E4_OUT/$G.wsg" "$E4_OUT/$G.csr"
    echo "[$(date +%T)] removed $E4_OUT/$G.wsg (and $G.csr if any)"
  fi
done
echo "[$(date +%T)] all done: ${graphs[*]}"
exit
}
