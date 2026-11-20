#!/usr/bin/env bash
# E3 step 3: instrumented runs (stats build, bin/sssp_stats) with phase logs.
# Same graphs x schedules x threads as the timing runs, -r 1. These numbers are
# used for imbalance / barrier-wait analysis only, NOT as timing data.
# Phase logs are gzipped into results/e3_imbalance/phase_logs/ (not committed).
#
#   run -c 12 -- bash scripts/exp/e3_run_stats.sh
source "$(dirname "$0")/e3_common.sh"
log_host run_stats

for g in "${GRAPHS[@]}"; do
  d=$(delta_of "$g")
  [ -n "$d" ] || { echo "no delta for $g: run e3_select_delta.sh first"; exit 1; }
  for s in "${SCHEDS[@]}"; do
    tag=$(sched_tag "$s")
    [ -f "$DONE/stats_${g}_$tag" ] && { echo "[$g $s] done, skipping"; continue; }
    tmp=$OUT/stats_${g}_$tag.tmp; plog=$PLOG/phases_${g}_$tag.csv
    rm -f "$tmp" "$plog" "$plog.gz"
    echo "[$g $s] delta=$d threads=$THREADS (stats build)"
    run_or_stop ./bin/sssp_stats -g "$CSR/$g.csr" -a delta-omp -d "$d" -t $THREADS --sched "$s" \
      --sources $SOURCES --seed $SEED -r 1 --verify -q --csv "$tmp" --phase-log "$plog"
    gzip -f "$plog"
    if [ ! -f "$OUT/stats.csv" ]; then cp "$tmp" "$OUT/stats.csv"; else tail -n +2 "$tmp" >> "$OUT/stats.csv"; fi
    rm -f "$tmp"; touch "$DONE/stats_${g}_$tag"
  done
done
echo "stats rows: $(($(wc -l < "$OUT/stats.csv") - 1))"
ls -la "$PLOG"
