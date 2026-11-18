#!/usr/bin/env bash
# E4: print the Delta list for GRAPH: the fastest Delta (median over reps) in
# $E4_RES/sweep/GRAPH.csv and its two neighbours in the sweep grid (fails if
# the best is at an edge of the grid). Light work; fine on the login node.
# Output (stdout): PREV,BEST,NEXT<TAB>BEST<TAB>E0_REF (or -)
set -euo pipefail
source "$(dirname "$0")/e4_env.sh"

G="${1:?usage: e4_pick_delta.sh GRAPH}"

CSV="$E4_RES/sweep/$G.csv"
[ -s "$CSV" ] || e4_die "no sweep for $G ($CSV)"
# CSV columns: ... 7=delta ... 10=time_ms ... 20=verified
awk -F, -v grid="$E4_SWEEP_DELTAS" -v ref="${E4_REF_DELTA[$G]:--}" '
  NR == 1 { next }
  $20 == 0 { bad = 1 }
  { k = ++cnt[$7]; t[$7, k] = $10 + 0 }
  END {
    if (bad) { print "sweep has a WRONG run" > "/dev/stderr"; exit 1 }
    for (x in cnt) {            # median of the reps for each delta
      m = cnt[x]
      for (i = 2; i <= m; i++) { v = t[x, i]; for (j = i - 1; j >= 1 && t[x, j] > v; j--) t[x, j + 1] = t[x, j]; t[x, j + 1] = v }
      best[x] = (m % 2) ? t[x, (m + 1) / 2] : (t[x, m / 2] + t[x, m / 2 + 1]) / 2
    }
    n = split(grid, d, ",")
    bi = 0
    for (i = 1; i <= n; i++) if (d[i] in best && (bi == 0 || best[d[i]] < best[d[bi]])) bi = i
    if (bi <= 1 || bi >= n) { print "best delta " d[bi] " is at the edge of the sweep grid" > "/dev/stderr"; exit 1 }
    printf "%s,%s,%s\t%s\t%s\n", d[bi - 1], d[bi], d[bi + 1], d[bi], ref
  }' "$CSV"
