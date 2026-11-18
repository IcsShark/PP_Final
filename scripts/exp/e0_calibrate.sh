#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PP_DATA_DIR=/u/cs/111/111550055/pp_data
mkdir -p results/profile results/e0_calibration
case "${1:-}" in
  setup)
    hostname > results/e0_calibration/hostname.txt
    lscpu > results/e0_calibration/lscpu.txt
    git rev-parse HEAD > results/e0_calibration/COMMIT.txt
    make test
    touch results/e0_calibration/tests.ok
    for g in NY CTR USA LJ OK kron23 urand23 grid2896; do
      bin/profile "$PP_DATA_DIR/csr/$g.csr" > "results/profile/$g.json.tmp"
      mv "results/profile/$g.json.tmp" "results/profile/$g.json"
    done
    ;;
  config)
    g=$2; algo=$3; d=$4; t=$5
    node=$(hostname)
    if [[ ! -f "results/e0_calibration/lscpu.$node.txt" ]]; then
      lscpu > "results/e0_calibration/lscpu.$node.txt"
    fi
    nproc
    taskset -p $$
    printf 'OMP_PROC_BIND=%s OMP_PLACES=%s\n' "${OMP_PROC_BIND-unset}" "${OMP_PLACES-unset}"
    out="results/e0_calibration/${g}_${algo}_${d}_${t}${6:+_allocation$6}"
    [[ ! -f "$out.done" ]] || exit 0
    cmd=(bin/sssp -g "$PP_DATA_DIR/csr/$g.csr" -a "$algo" -d "$d" -t "$t" --variant all --filter pop --sched dynamic,64 --sources 1 --seed 42 -r 3 --verify --csv "$out.csv" -q)
    { git rev-parse HEAD; hostname; date -Is; printf '%q ' "${cmd[@]}"; echo; } >> results/e0_calibration/META.txt
    if [[ -f "$out.csv" ]]; then mv "$out.csv" "$out.csv.partial.$(date +%s)"; fi
    timeout 1100 "${cmd[@]}"
    touch "$out.done"
    ;;
  *) echo 'usage: e0_calibrate.sh setup | config GRAPH ALGO DELTA THREADS' >&2; exit 2 ;;
esac
