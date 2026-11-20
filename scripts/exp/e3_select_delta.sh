#!/usr/bin/env bash
# E3 step 1: choose one "good" delta per graph.
# No E1 results on main yet (results/e1_*), so per the spec we run the cheap
# sweep (timing build, t=12, 1 source, 1 rep, default variant/filter/sched)
# and take the fastest delta.
#
#   run -c 12 -- bash scripts/exp/e3_select_delta.sh
#
# Output: results/e3_imbalance/delta_sweep.csv (all sweep runs)
#         results/e3_imbalance/delta.csv        (graph,delta,time_ms,reason)
source "$(dirname "$0")/e3_common.sh"
log_host select_delta

[ -f "$OUT/delta.csv" ] || echo "graph,delta,time_ms,reason" > "$OUT/delta.csv"
for g in "${GRAPHS[@]}"; do
  if [ -n "$(delta_of "$g")" ]; then echo "[$g] delta already chosen: $(delta_of "$g")"; continue; fi
  tmp=$OUT/sweep_$g.tmp; rm -f "$tmp"
  echo "[$g] sweeping delta ..."
  run_or_stop ./bin/sssp -g "$CSR/$g.csr" -d sweep -t 12 --sources 1 --seed $SEED -r 1 -q --csv "$tmp"
  # CSV columns: graph,algo,variant,filter,sched,threads,delta,source,rep,time_ms,...
  best=$(awk -F, 'NR > 1 { if (best == "" || $10 + 0 < t) { t = $10 + 0; best = $7 } } END { print best "," t }' "$tmp")
  if [ ! -f "$OUT/delta_sweep.csv" ]; then cp "$tmp" "$OUT/delta_sweep.csv"; else tail -n +2 "$tmp" >> "$OUT/delta_sweep.csv"; fi
  rm -f "$tmp"
  echo "$g,$best,fastest delta in sweep (t=12 1 source 1 rep; no E1 results on main)" >> "$OUT/delta.csv"
  echo "[$g] chosen delta,time_ms = $best"
done
cat "$OUT/delta.csv"
