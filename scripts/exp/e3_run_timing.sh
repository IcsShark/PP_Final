#!/usr/bin/env bash
# E3 step 2: timing runs (timing build, bin/sssp).
# graphs x schedules x threads {6,12}, --sources 4 -r 3. Every configuration
# is also verified against Dijkstra (--verify; outside the timed region).
# Resumable: each (graph, schedule) is appended to timing.csv only after it
# completes, and is skipped on later runs.
#
#   run -c 12 -- bash scripts/exp/e3_run_timing.sh
source "$(dirname "$0")/e3_common.sh"
log_host run_timing

for g in "${GRAPHS[@]}"; do
  d=$(delta_of "$g")
  [ -n "$d" ] || { echo "no delta for $g: run e3_select_delta.sh first"; exit 1; }
  for s in "${SCHEDS[@]}"; do
    tag=$(sched_tag "$s")
    [ -f "$DONE/timing_${g}_$tag" ] && { echo "[$g $s] done, skipping"; continue; }
    tmp=$OUT/timing_${g}_$tag.tmp; rm -f "$tmp"
    echo "[$g $s] delta=$d threads=$THREADS"
    run_or_stop ./bin/sssp -g "$CSR/$g.csr" -a delta-omp -d "$d" -t $THREADS --sched "$s" \
      --sources $SOURCES --seed $SEED -r 3 --verify -q --csv "$tmp"
    if [ ! -f "$OUT/timing.csv" ]; then cp "$tmp" "$OUT/timing.csv"; else tail -n +2 "$tmp" >> "$OUT/timing.csv"; fi
    rm -f "$tmp"; touch "$DONE/timing_${g}_$tag"
  done
done
echo "timing rows: $(($(wc -l < "$OUT/timing.csv") - 1))"
