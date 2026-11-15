#!/usr/bin/env bash
# End-to-end smoke test on small synthetic graphs (a few minutes at most).
# Run on a compute node:   run -c 6 -- bash scripts/smoke.sh
# Optional: THREADS=1,2,4,6 bash scripts/smoke.sh
set -euo pipefail
cd "$(dirname "$0")/.."

NPROC=$(nproc)
THREADS=${THREADS:-$(printf '%s\n' 1 2 4 "$NPROC" | sort -nu | paste -sd,)}
G=graphs/smoke
OUT=results/smoke
mkdir -p "$G" "$OUT"
rm -f "$OUT"/*.csv

echo "== nproc=$NPROC threads=$THREADS OMP_PROC_BIND=${OMP_PROC_BIND:-unset} OMP_PLACES=${OMP_PLACES:-unset}"

echo "== generating graphs"
./bin/gen kron  --scale 16 --degree 16 -o "$G/kron16.csr"
./bin/gen urand --scale 16 --degree 16 -o "$G/urand16.csr"
./bin/gen grid  --side 256            -o "$G/grid256.csr"

echo "== DIMACS conversion"
cat > "$G/tiny.gr" <<'EOF'
c tiny road-style graph
p sp 4 5
a 1 2 3
a 2 3 4
a 1 3 10
a 3 4 1
a 4 1 2
EOF
./bin/convert "$G/tiny.gr" -o "$G/tiny.csr" --emit-wel "$G/tiny.wel"
./bin/sssp -g "$G/tiny.csr" --source 0 -d 1,4 -t 1,2 -a dijkstra,delta-seq,delta-omp --verify -q

for g in kron16 urand16 grid256; do
  echo "== $g"
  ./bin/profile "$G/$g.csr"
  # all algorithms, full delta sweep, every thread count, verified against Dijkstra
  ./bin/sssp -g "$G/$g.csr" -a dijkstra,delta-seq,delta-omp -d sweep -t "$THREADS" \
    --sources 2 -r 1 --verify -q --csv "$OUT/sweep.csv"
  # design variants
  for v in all lh; do
    for f in pop merge; do
      ./bin/sssp -g "$G/$g.csr" -a delta-omp --variant $v --filter $f -d 4096 -t "$THREADS" \
        --sources 2 -r 1 --verify -q --csv "$OUT/variants.csv"
    done
  done
  for s in static dynamic,64 guided; do
    ./bin/sssp -g "$G/$g.csr" -a delta-omp --sched $s -d 4096 -t "$NPROC" \
      --sources 2 -r 1 --verify -q --csv "$OUT/sched.csv"
  done
  # instrumented build: counters + per-phase log
  ./bin/sssp_stats -g "$G/$g.csr" -a delta-seq,delta-omp -d 1024,16384 -t "$NPROC" \
    --sources 1 -r 1 --verify -q --csv "$OUT/stats.csv" --phase-log "$OUT/phases.csv"
done

echo
echo "== smoke test PASSED. CSV files:"
wc -l "$OUT"/*.csv
