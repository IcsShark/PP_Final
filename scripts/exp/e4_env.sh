# E4 (GAPBS baseline): shared settings, sourced by the other e4_*.sh scripts.
# Every path can be overridden from the environment.
#
#   E4_RAW      raw .gz datasets (scripts/fetch-datasets.sh, md5-checked)
#   E4_REF_CSR  reference CSRs that E0-E2 use; regenerated CSRs must `cmp` equal
#   E4_OUT      generated .csr / .wsg (.wel is temporary, in node-local tmp)
#   GAPBS_DIR   GAPBS checkout, built with `run -c 4 -- make -j4`
#   E4_RES      results directory inside the repo

E4_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
E4_RAW="${E4_RAW:-$HOME/pp_data/raw}"
E4_REF_CSR="${E4_REF_CSR:-/u/cs/111/111550055/pp_data/csr}"
E4_OUT="${E4_OUT:-$HOME/pp_data/gapbs}"
GAPBS_DIR="${GAPBS_DIR:-$HOME/gapbs}"
E4_RES="${E4_RES:-$E4_REPO/results/e4_gapbs}"

E4_GRAPHS=(NY CTR USA LJ OK kron23 urand23 grid2896)
E4_THREADS=(1 6 12)

# Reference Delta from E0 calibration (spec section 4.4). Recorded only: on NY
# t=12 the reference (256) was clearly slower than 512, so every graph gets the
# same cheap sweep (e4_sweep.sh) and its fastest Delta is used.
declare -A E4_REF_DELTA=([NY]=256 [CTR]=512 [USA]=1024 [LJ]=512)

# Sweep grid: 2^6 .. 2^18.
E4_SWEEP_DELTAS="64,128,256,512,1024,2048,4096,8192,16384,32768,65536,131072,262144"
# Per-graph extension: on grid2896 the time still fell at 2^18 (the edge of
# the default grid), so its sweep continues past w_max up to 2^24.
declare -A E4_SWEEP_DELTAS_FOR=([grid2896]="$E4_SWEEP_DELTAS,524288,1048576,2097152,4194304,8388608,16777216")
e4_sweep_deltas() { echo "${E4_SWEEP_DELTAS_FOR[$1]:-$E4_SWEEP_DELTAS}"; }

# Graphs whose shared reference CSR is NOT used. The reference LJ.csr does not
# match a rebuild from the md5-checked raw file: 20 vertices differ and it has
# 18 duplicate edges, which build_csr cannot produce (see e4_check_ref.sh).
# User decision (2026-11-19): run ours and GAPBS on the regenerated LJ.
E4_FRESH=(LJ)
e4_fresh() { local g; for g in "${E4_FRESH[@]}"; do [ "$g" = "$1" ] && return 0; done; return 1; }
# CSR that ours reads for GRAPH.
e4_csr() { if e4_fresh "$1"; then echo "$E4_OUT/$1.csr"; else echo "$E4_REF_CSR/$1.csr"; fi; }

# Node-local scratch for the current job (removed by the caller's trap).
e4_mktmp() { mktemp -d "${TMPDIR:-/tmp}/e4_${USER}_XXXXXX"; }

e4_die() { echo "E4 ERROR: $*" >&2; exit 1; }

# ---- driver helpers (login node; e4_all.sh, e4_suggested.sh)
ok() { [ -f "$E4_RES/status/$1" ] && grep -q '^OK' "$E4_RES/status/$1"; }
# The job writes its status on the compute node; the login node's NFS cache can
# take up to a minute to show a new file or its new contents.
ok_wait() { for _ in $(seq 1 30); do ok "$1" && return 0; sleep 3; done; return 1; }
# Wait (up to ~90 s) until FILE shows LINES lines on this node (NFS cache).
wait_lines() { for _ in $(seq 1 30); do [ -f "$1" ] && [ "$(wc -l < "$1")" = "$2" ] && return 0; sleep 3; done; return 1; }
job() { # status-name script args...   (one compute job, whole node)
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
