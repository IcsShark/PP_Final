#!/usr/bin/env bash
# E4 section 4.5 (optional): GAPBS's own suggested Delta. Its benchmark
# (benchmark/bench.mk) runs the road graph with -d50000; its -d2 for kron/urand
# assumes GAPBS's generator weights (1..255), not ours (1..2^18), so only the
# road graphs are run. Times ours and GAPBS at Delta=50000, t = 1, 6, 12, with
# the same e4_run.sh as the main runs (rows land next to them in raw/).
#
#   module load pp
#   nohup bash scripts/exp/e4_suggested.sh > ~/e4_suggested.log 2>&1 &
{ # read the whole script first: replacing this file mid-run is then safe
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"
command -v run > /dev/null || e4_die "'run' not found; module load pp first"
cd "$E4_REPO"
while [ -n "$(squeue -u "$USER" -h 2>/dev/null)" ]; do sleep 10; done

D=50000
for G in NY CTR USA; do
  todo=0
  for T in "${E4_THREADS[@]}"; do ok "run_${G}_t${T}_d${D}" || todo=1; done
  [ "$todo" = 1 ] || { echo "[$(date +%T)] skip $G (done)"; continue; }
  # the main pass deleted the .wsg: rebuild it (same checks as before)
  [ -f "$E4_OUT/$G.wsg" ] || rm -f "$E4_RES/status/prep_$G"
  job "prep_$G" scripts/exp/e4_prep.sh "$G"
  for T in "${E4_THREADS[@]}"; do
    job "run_${G}_t${T}_d${D}" scripts/exp/e4_run.sh "$G" "$T" "$D"
  done
  [ "${E4_KEEP_WSG:-0}" = 1 ] || { rm -f "$E4_OUT/$G.wsg"; echo "[$(date +%T)] removed $E4_OUT/$G.wsg"; }
done
echo "[$(date +%T)] all done: suggested Delta $D"
exit
}
