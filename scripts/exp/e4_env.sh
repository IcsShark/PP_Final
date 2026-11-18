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
