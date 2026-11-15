#!/usr/bin/env python3
"""Generate the SSSP correctness testcases in tests/testcase/.

Format (same as the member's examples/ files):

  <name>.in.txt     TEST
                    n m s           (vertices 1..n, s = source)
                    u v w           (m directed edges, w >= 0 integer)
                    ...             (repeated TEST times)
  <name>.ans.txt    one line per test: dist(s, 1..n) separated by spaces, -1 = unreachable

Answers are computed here with an independent Python Dijkstra, so they do not
depend on the C++ code under test. The output is deterministic (fixed seeds).

  python3 tests/gen_testcases.py                       # regenerate the synthetic files
  python3 tests/gen_testcases.py --import-examples examples
                                                       # also copy examples/{dense,sparse}.{in,ac}
"""
import argparse
import heapq
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "testcase")


def dijkstra(n, edges, s):
    adj = [[] for _ in range(n + 1)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [None] * (n + 1)
    dist[s] = 0
    pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d != dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if dist[v] is None or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return [(-1 if x is None else x) for x in dist[1:]]


def write_cases(name, cases):
    """cases: list of (n, edges, s) with 1-indexed vertices."""
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".in.txt"), "w", newline="\n") as f:
        f.write(f"{len(cases)}\n")
        for n, edges, s in cases:
            f.write(f"{n} {len(edges)} {s}\n")
            f.writelines(f"{u} {v} {w}\n" for u, v, w in edges)
    with open(os.path.join(OUT, name + ".ans.txt"), "w", newline="\n") as f:
        for n, edges, s in cases:
            f.write(" ".join(map(str, dijkstra(n, edges, s))) + "\n")
    print(f"wrote {name}: {len(cases)} tests")


def both_directions(und, weights):
    out = []
    for (u, v), w in zip(und, weights):
        out.append((u, v, w))
        out.append((v, u, w))
    return out


def rand_weights(rng, k, lo, hi):  # uniform integers in [lo, hi)
    return [rng.randrange(lo, hi) for _ in range(k)]


def pick_sources(rng, n, edges, k):
    has_out = sorted({u for u, _, _ in edges})
    return rng.sample(has_out, min(k, len(has_out)))


def gen_urand(rng, scale, degree):
    n = 1 << scale
    return n, [(rng.randint(1, n), rng.randint(1, n)) for _ in range(n * degree // 2)]


def gen_kron(rng, scale, degree, A=0.57, B=0.19, C=0.19):
    n = 1 << scale
    und = []
    for _ in range(n * degree // 2):
        u = v = 0
        for _ in range(scale):
            r = rng.random()
            u <<= 1
            v <<= 1
            if r < A:
                pass
            elif r < A + B:
                v |= 1
            elif r < A + B + C:
                u |= 1
            else:
                u |= 1
                v |= 1
        und.append((u + 1, v + 1))
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    return n, [(perm[u - 1], perm[v - 1]) for u, v in und]


def gen_grid(side):
    und = []
    for r in range(side):
        for c in range(side):
            i = r * side + c + 1
            if c + 1 < side:
                und.append((i, i + 1))
            if r + 1 < side:
                und.append((i, i + side))
    return side * side, und


def handmade():
    cases = []
    # small DAG-like graph; vertices 5, 6 unreachable from 1
    cases.append((6, [(1, 2, 4), (1, 3, 1), (3, 2, 2), (2, 4, 1), (3, 4, 5), (5, 1, 1)], 1))
    # zero-weight edges and a zero-weight cycle
    cases.append((5, [(1, 2, 0), (2, 3, 0), (3, 2, 0), (3, 4, 3), (1, 4, 5), (4, 5, 0)], 1))
    # single vertex, no edges
    cases.append((1, [], 1))
    # self loops and parallel edges (the minimum parallel weight must win)
    cases.append((3, [(1, 1, 1), (1, 2, 5), (1, 2, 3), (2, 3, 2), (2, 3, 9), (3, 3, 0)], 1))
    # long unit-weight chain: many buckets, one vertex per phase
    cases.append((60, [(i, i + 1, 1) for i in range(1, 60)], 1))
    # weights near 2^32: path sums exceed 32 bits (dist must be 64-bit)
    big = 4_000_000_000
    cases.append((4, [(1, 2, big), (2, 3, big), (3, 4, big), (1, 4, 4_294_967_295)], 1))
    # star: one high-degree source (load imbalance inside one phase)
    rng = random.Random(7)
    cases.append((300, [(1, v, rng.randrange(1, 1000)) for v in range(2, 301)], 1))
    # source in the middle of a two-way path
    cases.append((9, [(i, i + 1, 2) for i in range(1, 9)] + [(i + 1, i, 3) for i in range(1, 9)], 5))
    write_cases("handmade", cases)


def synthetic(name, graph_fn, weight_ranges, seed, sources=2):
    rng = random.Random(seed)
    n, und = graph_fn(rng)
    cases = []
    for lo, hi in weight_ranges:
        edges = both_directions(und, rand_weights(rng, len(und), lo, hi))
        for s in pick_sources(rng, n, edges, sources):
            cases.append((n, edges, s))
    write_cases(name, cases)


def import_examples(src_dir):
    """Copy the member's examples/{dense,sparse}.{in,ac} with LF line endings."""
    for name in ("dense", "sparse"):
        for ext, out_ext in ((".in", ".in.txt"), (".ac", ".ans.txt")):
            with open(os.path.join(src_dir, name + ext), "r") as f:
                text = f.read().replace("\r\n", "\n")
            with open(os.path.join(OUT, name + out_ext), "w", newline="\n") as f:
                f.write(text)
        print(f"imported {name} from {src_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--import-examples", metavar="DIR", help="also copy dense/sparse from the examples folder")
    args = ap.parse_args()

    handmade()
    big = 1_000_000_000
    synthetic("urand", lambda r: gen_urand(r, 10, 6),
              [(1, 2), (0, 4), (1, 1000), (1, 1 << 18), (0, big)], seed=11)
    synthetic("kron", lambda r: gen_kron(r, 10, 8),
              [(1, 1 << 18), (0, 10), (1, big)], seed=12)
    synthetic("grid", lambda r: gen_grid(24),
              [(1, 100), (1, 1 << 18), (0, 4)], seed=13)
    if args.import_examples:
        import_examples(args.import_examples)


if __name__ == "__main__":
    main()
