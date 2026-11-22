#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out="$PWD/results/e5_perf"
raw="${E5_RAW_DIR:-$HOME/devin/results_raw/e5}"
mkdir -p "$out" "$raw"
if [[ "${1:-}" == --events ]]; then
    exec >"$raw/extra_events.log" 2>&1
    hostname -f
    for event in cycle_activity.stalls_l3_miss cycle_activity.stalls_mem_any \
        mem_load_retired.l3_miss offcore_requests.all_data_rd LLC-load-misses; do
        printf '\nEVENT=%s\n' "$event"
        if perf stat -x, -o "$raw/probe_${event}.perf" -e "$event" \
            -- python3 -c 'print(sum(i * i for i in range(1000000)))'; then
            cat "$raw/probe_${event}.perf"
        else
            printf 'UNSUPPORTED_OR_UNAVAILABLE=%s\n' "$event"
            cat "$raw/probe_${event}.perf"
        fi
    done
elif [[ "${1:-}" == --compute ]]; then
    exec >"$raw/probe.log" 2>&1
    set -x
    date --iso-8601=seconds
    hostname -f
    git rev-parse HEAD
    lscpu
    nproc
    taskset -p $$
    printf 'OMP_PROC_BIND=%s OMP_PLACES=%s\n' "${OMP_PROC_BIND:-unset}" "${OMP_PLACES:-unset}"
    cat /proc/sys/kernel/perf_event_paranoid
    perf --version
    perf list >"$out/perf_list.txt" 2>&1
    ./bin/sssp --help >"$raw/sssp_help.txt" 2>&1
    perf stat -x, -o "$raw/event_probe.perf" \
        -e cycles,instructions,cache-references,cache-misses \
        -- python3 -c 'print(sum(i * i for i in range(1000000)))'
else
    module load pp
    exec 9>"$raw/campaign.lock"
    flock -n 9
    [[ -z "$(squeue -h -u "$USER")" ]] || { echo 'Scheduler is not empty; refusing to queue'; exit 1; }
    run -c 4 -- make -j4 >"$raw/build.log" 2>&1
    run -c 12 -- bash scripts/exp/e5_probe.sh --compute >"$raw/probe_scheduler.log" 2>&1
fi
