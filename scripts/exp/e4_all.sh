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
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"
command -v run > /dev/null || e4_die "'run' not found; module load pp first"
cd "$E4_REPO"

ok() { [ -f "$E4_RES/status/$1" ] && grep -q '^OK' "$E4_RES/status/$1"; }
# The job writes its status on the compute node; the login node's NFS cache can
# take up to a minute to show a new file or its new contents.
ok_wait() { for _ in $(seq 1 30); do ok "$1" && return 0; sleep 3; done; return 1; }
job() { # status-name script args...
  local st=$1; shift
  if ok "$st"; then echo "[$(date +%T)] skip $st (OK)"; return 0; fi
  echo "[$(date +%T)] submit $st"
  # run always exits 0. It prints the job's output (a fresh slurm-*.out, so no
  # stale NFS cache) when the job ends; every e4 step ends with "== ... OK in".
  local out
  out=$(run -c 12 -- bash "$@" 2>&1 || true)
  grep -q '^== .* OK in [0-9]*s$' <<< "$out" || ok_wait "$st" || e4_die "$st: $(cat "$E4_RES/status/$st" 2>/dev/null || echo 'no status (job killed? 30 min limit)')"
  echo "[$(date +%T)] done   $st: $(grep -m1 '^== .* OK in' <<< "$out" || cat "$E4_RES/status/$st" 2>/dev/null)"
}

# Wait (up to ~90 s) until FILE shows LINES lines on this node (NFS cache).
wait_lines() { for _ in $(seq 1 30); do [ -f "$1" ] && [ "$(wc -l < "$1")" = "$2" ] && return 0; sleep 3; done; return 1; }

# Never overlap with a job left over from an earlier driver (pp_qos: 1 job).
while [ -n "$(squeue -u "$USER" -h 2>/dev/null)" ]; do sleep 10; done

graphs=("$@")
[ ${#graphs[@]} -gt 0 ] || graphs=("${E4_GRAPHS[@]}")
mkdir -p "$E4_RES"
NSWEEP=$(( $(tr ',' '\n' <<< "$E4_SWEEP_DELTAS" | wc -l) * 3 + 1 ))
for G in "${graphs[@]}"; do
  if ok "iters_$G"; then echo "[$(date +%T)] skip $G (done)"; continue; fi
  # .wsg deleted after an earlier, partly finished pass: rebuild it.
  [ -f "$E4_OUT/$G.wsg" ] || rm -f "$E4_RES/status/prep_$G"
  job "prep_$G" scripts/exp/e4_prep.sh "$G"
  job "sweep_$G" scripts/exp/e4_sweep.sh "$G"
  wait_lines "$E4_RES/sweep/$G.csv" "$NSWEEP" || e4_die "sweep/$G.csv incomplete on the login node"
  IFS=$'\t' read -r DELTAS BEST REF < <(bash scripts/exp/e4_pick_delta.sh "$G")
  [ -n "${BEST:-}" ] || e4_die "no Delta picked for $G"
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
    rm -f "$E4_OUT/$G.wsg"
    echo "[$(date +%T)] removed $E4_OUT/$G.wsg"
  fi
done
echo "[$(date +%T)] all done: ${graphs[*]}"
