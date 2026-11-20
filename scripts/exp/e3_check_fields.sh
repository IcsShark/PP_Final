#!/usr/bin/env bash
# E3 acceptance check for the code change (spec section 4):
# run sssp_stats --phase-log on NY and check that the new per-phase fields are
# sane: edges/T <= max_thread_edges <= edges, max_thread_edges >= max_vertex_edges,
# 0 <= mean_wait_us <= max_wait_us.
#
#   run -c 12 -- bash scripts/exp/e3_check_fields.sh
source "$(dirname "$0")/e3_common.sh"
log_host check_fields

log=$OUT/check_NY_phases.tmp; rm -f "$log"
run_or_stop ./bin/sssp_stats -g "$CSR/NY.csr" -a delta-omp -d 256 -t 6,12 --sources 2 --seed $SEED -r 1 \
  --verify -q --phase-log "$log"
# columns: graph,algo,variant,filter,threads,delta,source,phase,bucket,heavy,frontier,expanded,
#          edges,max_vertex_edges,max_thread_edges,max_wait_us,mean_wait_us
awk -F, 'NR == 1 { next }
  { n++; T = $5; e = $13; mv = $14; mt = $15; mx = $16; mn = $17
    if (mt > e || mt * T < e || mt < mv || mn < 0 || mn > mx + 1e-6) { bad++; if (bad <= 5) print "BAD row " NR ": " $0 }
    if (e > 0) { sum_ratio += mt / (e / T); m++ } }
  END { printf "NY phase rows=%d bad=%d mean(max_thread_edges/(edges/T))=%.3f\n", n, bad, (m ? sum_ratio / m : 0)
        exit (bad > 0) }' "$log" | tee "$OUT/check_fields.txt"
rc=${PIPESTATUS[0]}
rm -f "$log"
[ "$rc" -eq 0 ] && echo "field check PASSED" | tee -a "$OUT/check_fields.txt" || { echo "field check FAILED"; exit 1; }
