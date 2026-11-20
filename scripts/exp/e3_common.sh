#!/usr/bin/env bash
# Shared settings for the E3 (load imbalance, Q3a) experiment.
# Sourced by the other scripts/exp/e3_*.sh scripts; see experiment/E3-experiment-spec.md.

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO" || exit 1

export PP_DATA_DIR=${PP_DATA_DIR:-/u/cs/111/111550055/pp_data}
CSR=$PP_DATA_DIR/csr                       # read-only shared data
OUT=$REPO/results/e3_imbalance
PLOG=$OUT/phase_logs                        # gzipped phase logs (not committed)
DONE=$OUT/.done                             # resume markers (not committed)

GRAPHS=(LJ OK kron23 USA)                   # LJ/OK/kron23 have hubs; USA is the no-hub control
SCHEDS=(static dynamic,1 dynamic,64 dynamic,256 guided)
THREADS=6,12
SOURCES=4
SEED=42

mkdir -p "$OUT" "$PLOG" "$DONE"
[ -f "$OUT/.gitignore" ] || printf 'phase_logs/\n.done/\n*.tmp\n' > "$OUT/.gitignore"

# Record which compute node / CPU each job ran on (for META.txt).
log_host() {
  {
    echo "== $(date '+%F %T') $1 on $(hostname) nproc=$(nproc) SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
    lscpu | grep -E 'Model name|^CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|L3'
  } >> "$OUT/hosts.log"
}

# Delta chosen for a graph by e3_select_delta.sh (empty if not chosen yet).
delta_of() { awk -F, -v g="$1" '$1 == g { print $2 }' "$OUT/delta.csv" 2>/dev/null; }

sched_tag() { echo "${1//,/_}"; }           # "dynamic,64" -> "dynamic_64" for file names

# Run a command; if it fails (incl. a --verify mismatch: exit 1), stop the whole
# experiment as required by the spec, leaving a FAILED marker.
run_or_stop() {
  "$@"
  local rc=$?
  if [ $rc -ne 0 ]; then
    echo "FAILED (exit $rc): $*" | tee -a "$OUT/FAILED"
    exit 1
  fi
}
