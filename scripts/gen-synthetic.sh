#!/bin/bash
G=$PP_DATA_DIR/csr
run -c 1 -- ./bin/gen kron  --scale 23 --degree 16 --seed 1 -o $G/kron23.csr
run -c 1 -- ./bin/gen urand --scale 23 --degree 16 --seed 1 -o $G/urand23.csr
run -c 1 -- ./bin/gen grid  --side 2896            --seed 1 -o $G/grid2896.csr   # 2896² ≈ 2^23 vertices
