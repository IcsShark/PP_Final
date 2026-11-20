#!/usr/bin/env python3
"""E3 helper: top out-degrees (hubs) of each graph, read straight from the .csr
offsets array. Standard library only (the cluster's Python has no numpy).

  run -c 12 -- python3 scripts/exp/e3_hub_degrees.py

Writes results/e3_imbalance/hub_degrees.csv: graph,rank,vertex,degree
Used by the analysis to check whether the worst phases' max_vertex_edges is a hub.
"""
import array
import heapq
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CSR = os.path.join(os.environ.get("PP_DATA_DIR", "/u/cs/111/111550055/pp_data"), "csr")
OUT = os.path.join(REPO, "results", "e3_imbalance", "hub_degrees.csv")
GRAPHS = ["LJ", "OK", "kron23", "USA"]
TOP = 50


def top_degrees(path, k):
    with open(path, "rb") as f:
        magic, n, m, flags, _ = struct.unpack("<8sQQQQ", f.read(40))
        if magic != b"SSSPCSR1":
            sys.exit(f"{path}: not a SSSPCSR1 file")
        off = array.array("Q")
        off.fromfile(f, n + 1)
    if sys.byteorder != "little":
        off.byteswap()
    degs = ((off[u + 1] - off[u], u) for u in range(n))
    return n, m, heapq.nlargest(k, degs)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as out:
        out.write("graph,rank,vertex,degree\n")
        for g in GRAPHS:
            n, m, top = top_degrees(os.path.join(CSR, g + ".csr"), TOP)
            for r, (d, u) in enumerate(top, 1):
                out.write(f"{g},{r},{u},{d}\n")
            print(f"{g}: n={n} m={m} top degrees: {[d for d, _ in top[:5]]}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
