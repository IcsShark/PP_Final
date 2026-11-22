#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
raw="${E5_RAW_DIR:-$HOME/devin/results_raw/e5}"
events=cycles,instructions,cache-references,cache-misses,cycle_activity.stalls_l3_miss,cycle_activity.stalls_mem_any,mem_load_retired.l3_miss,offcore_requests.all_data_rd
if [[ "${1:-}" == --compute ]]; then
    graph="$2"
    threads="$3"
    read -r delta variant filter < <(python3 - "$graph" <<'PY'
import json
import pathlib
import sys
graph = sys.argv[1]
delta = {'LJ': 4096, 'USA': 32768, 'OK': 1024, 'urand23': 1024}[graph]
setting = json.loads(pathlib.Path(f'results/e2_scaling/{graph}.json').read_text())
assert delta in setting['deltas']
print(delta, setting['variant'], setting['filter'])
PY
    )
    [[ "$threads" =~ ^(1|2|4|6|8|12)$ ]]
    job="$raw/$graph/t$threads"
    [[ ! -e "$job" ]] || { echo "Existing incomplete job: $job"; exit 1; }
    mkdir -p "$job"
    exec >"$job/job.log" 2>&1
    trap 'touch "$job/FAILED"' ERR
    hostname -f >"$job/hostname.txt"
    date --iso-8601=seconds
    git rev-parse HEAD
    nproc
    taskset -p $$
    printf 'OMP_PROC_BIND=%s OMP_PLACES=%s\n' "${OMP_PROC_BIND:-unset}" "${OMP_PLACES:-unset}"
    export OMP_NUM_THREADS="$threads"
    base=(./bin/sssp -g "/u/cs/111/111550055/pp_data/csr/$graph.csr"
        -a delta-omp -d "$delta" -t "$threads" --variant "$variant" --filter "$filter"
        --sched dynamic,64 --sources 4 --seed 42)
    checked() {
        local csv="$1" log="$2" expected="$3" verified="$4"
        python3 - "$csv" "$log" "$expected" "$verified" <<'PY'
import csv
import pathlib
import re
import sys
path, log, expected, verified = sys.argv[1:]
assert not re.search(r'WRONG|MISMATCH|verified=0', pathlib.Path(log).read_text()), log
with open(path) as stream:
    rows = list(csv.DictReader(stream))
assert len(rows) == int(expected), (path, len(rows), expected)
assert len({r['source'] for r in rows}) == 4, path
assert all(r['verified'] == verified and r['stats_build'] == '0' for r in rows), path
assert all(float(r['time_ms']) > 0 for r in rows), path
print(f'PASS: {path}: {len(rows)} timing-build rows, verified={verified}')
PY
    }
    if [[ ! -f "$raw/$graph/verified.done" ]]; then
        printf '%q ' "${base[@]}" -r 1 --verify --csv "$raw/$graph/verify.csv" -q
        printf '\n'
        "${base[@]}" -r 1 --verify --csv "$raw/$graph/verify.csv" -q >"$raw/$graph/verify.log" 2>&1
        checked "$raw/$graph/verify.csv" "$raw/$graph/verify.log" 4 1
        touch "$raw/$graph/verified.done"
    fi
    for rep in 1 2 3; do
        for kind in A B; do
            repetitions=1
            [[ "$kind" == A ]] || repetitions=6
            prefix="$job/${kind}${rep}"
            command=(perf stat -x, -o "$prefix.perf" -e "$events" --
                "${base[@]}" -r "$repetitions" --csv "$prefix.csv" -q)
            printf '%q ' "${command[@]}"
            printf '\n'
            "${command[@]}" >"$prefix.log" 2>&1
            checked "$prefix.csv" "$prefix.log" "$((4 * repetitions))" -1
        done
    done
    python3 analysis/e5_analysis.py --check-job "$job"
    touch "$job/DONE"
    date --iso-8601=seconds
else
    module load pp
    mkdir -p "$raw"
    exec 9>"$raw/campaign.lock"
    flock -n 9
    graphs=(LJ USA)
    [[ "${1:-}" != --optional ]] || graphs=(OK urand23)
    if [[ "${1:-}" != '' && "${1:-}" != --optional ]]; then graphs=("$1"); fi
    for graph in "${graphs[@]}"; do
        threads_list=(1 2 4 6 8 12)
        [[ -z "${2:-}" ]] || threads_list=("$2")
        for threads in "${threads_list[@]}"; do
            [[ ! -f "$raw/$graph/t$threads/DONE" ]] || continue
            [[ -z "$(squeue -h -u "$USER")" ]] || { echo 'Scheduler is not empty; refusing to queue'; exit 1; }
            run -c 12 -- timeout 1700 bash scripts/exp/e5_run.sh --compute "$graph" "$threads" \
                >"$raw/${graph}_t${threads}.scheduler.log" 2>&1
            python3 analysis/e5_analysis.py --raw "$raw" --csv-only
        done
    done
fi
