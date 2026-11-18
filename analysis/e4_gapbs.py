# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "matplotlib"]
# ///
"""E4 analysis: ours (delta-omp) vs GAPBS sssp on identical graphs/sources/Delta.

    uv run analysis/e4_gapbs.py [RESULTS_DIR]      (default results/e4_gapbs)

Reads   RESULTS_DIR/raw/*.ours.csv, *.gapbs.csv (only runs whose status/run_* is OK),
        deltas.csv, sweep/*.csv, iters/*.csv
Writes  RESULTS_DIR/e4_summary.csv   graph x threads x Delta: ours, GAPBS, ratio
        RESULTS_DIR/e4_summary.md    the same as a Markdown table (best Delta marked),
                                     plus GAPBS iterations vs our phases
        RESULTS_DIR/plots/e4_bars_best_delta.{pdf,png}
        RESULTS_DIR/plots/e4_ratio_best_delta.{pdf,png}
        RESULTS_DIR/plots/e4_sweep.{pdf,png}

Time of one (impl, graph, threads, Delta, source) = median over its 3 trials;
the per-configuration time is the mean of those medians over the 4 sources.
ratio = GAPBS / ours, so ratio > 1 means ours is faster.
"""
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

GRAPHS = ["NY", "CTR", "USA", "LJ", "OK", "kron23", "urand23", "grid2896"]
THREADS = [1, 6, 12]

# Reference categorical palette (light mode), slots 1-3; text/surface tokens.
C_OURS, C_GAPBS = "#2a78d6", "#eb6834"
C_T = {1: "#2a78d6", 6: "#eb6834", 12: "#1baf7a"}
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.titlecolor": INK, "axes.titlesize": 11, "axes.titleweight": "bold",
    "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "legend.frameon": False, "axes.axisbelow": True,
})


def finished(res: Path, f: Path) -> bool:
    """Only use a run whose job reported OK (skips runs still in progress)."""
    tag = f.name.split(".")[0]
    st = res / "status" / f"run_{tag}"
    return st.exists() and st.read_text().startswith("OK")


def load(res: Path):
    ours_files = [f for f in sorted((res / "raw").glob("*.ours.csv")) if finished(res, f)]
    gap_files = [f for f in sorted((res / "raw").glob("*.gapbs.csv")) if finished(res, f)]
    if not ours_files or not gap_files:
        sys.exit(f"no raw CSVs under {res / 'raw'}")
    ours = pd.concat([pd.read_csv(f) for f in ours_files], ignore_index=True)
    ours = ours[ours.algo == "delta-omp"].rename(columns={"rep": "trial"})
    ours["impl"] = "ours"
    gap = pd.concat([pd.read_csv(f) for f in gap_files], ignore_index=True)
    cols = ["impl", "graph", "threads", "delta", "source", "trial", "time_ms", "verified"]
    runs = pd.concat([ours[cols], gap[cols]], ignore_index=True)
    bad = runs[runs.verified != 1]
    if len(bad):
        print("WARNING: runs that did not verify:\n", bad.to_string(index=False))
    deltas = pd.read_csv(res / "deltas.csv")
    return runs, deltas


def summarize(runs: pd.DataFrame, deltas: pd.DataFrame) -> pd.DataFrame:
    per_src = runs.groupby(["impl", "graph", "threads", "delta", "source"]).time_ms.median().reset_index()
    per_cfg = (per_src.groupby(["impl", "graph", "threads", "delta"])
               .agg(time_ms=("time_ms", "mean"), sources=("source", "nunique")).reset_index())
    wide = per_cfg.pivot_table(index=["graph", "threads", "delta"], columns="impl",
                               values=["time_ms", "sources"]).reset_index()
    wide.columns = ["graph", "threads", "delta"] + [f"{a}_{b}" for a, b in wide.columns[3:]]
    wide = wide.rename(columns={"time_ms_ours": "ours_ms", "time_ms_gapbs": "gapbs_ms"})
    wide["ratio_gapbs_over_ours"] = wide.gapbs_ms / wide.ours_ms
    best = dict(zip(deltas.graph, deltas.best_delta))
    wide["best_delta"] = [best.get(g) == d for g, d in zip(wide.graph, wide.delta)]
    wide["graph"] = pd.Categorical(wide.graph, [g for g in GRAPHS if g in set(wide.graph)], ordered=True)
    return wide.sort_values(["graph", "threads", "delta"]).reset_index(drop=True)


def write_tables(s: pd.DataFrame, res: Path):
    out = s[["graph", "threads", "delta", "best_delta", "ours_ms", "gapbs_ms", "ratio_gapbs_over_ours",
             "sources_ours", "sources_gapbs"]]
    out.to_csv(res / "e4_summary.csv", index=False, float_format="%.4f")
    lines = ["| graph | t | Δ | ours (ms) | GAPBS (ms) | GAPBS / ours |", "|---|---:|---:|---:|---:|---:|"]
    for r in out.itertuples():
        d = f"**{r.delta}**" if r.best_delta else (f"{r.delta}†" if r.delta == 50000 else f"{r.delta}")
        lines.append(f"| {r.graph} | {r.threads} | {d} | {r.ours_ms:.2f} | {r.gapbs_ms:.2f} | "
                     f"{r.ratio_gapbs_over_ours:.2f} |")
    text = ("Mean over 4 sources of the median of 3 trials. **Bold Δ** = best Δ from the sweep. "
            "† = GAPBS's suggested road Δ (spec 4.5). GAPBS / ours > 1 means ours is faster.\n\n" + "\n".join(lines) + "\n")
    # Spec 4.5: GAPBS's suggested road Delta (bench.mk: -d50000) vs the best of our sweep.
    sug = s[s.delta == 50000]
    if len(sug):
        rows = ["| graph | t | GAPBS @ Δ=50000 (ms) | GAPBS @ our best Δ (ms) | ours @ best Δ (ms) |",
                "|---|---:|---:|---:|---:|"]
        for r in sug.itertuples():
            b = s[(s.graph == r.graph) & (s.threads == r.threads) & s.best_delta]
            if len(b):
                rows.append(f"| {r.graph} | {r.threads} | {r.gapbs_ms:.2f} | {b.gapbs_ms.iloc[0]:.2f} "
                            f"(Δ={b.delta.iloc[0]}) | {b.ours_ms.iloc[0]:.2f} |")
        text += ("\nGAPBS's own suggested Δ for road graphs (benchmark/bench.mk: `-d50000`), spec 4.5.\n\n"
                 + "\n".join(rows) + "\n")
    it_files = sorted((res / "iters").glob("*.csv"))
    if it_files:
        it = pd.concat([pd.read_csv(f) for f in it_files], ignore_index=True)
        it["graph"] = pd.Categorical(it.graph, [g for g in GRAPHS if g in set(it.graph)], ordered=True)
        it = it.sort_values("graph")
        it.to_csv(res / "e4_iters.csv", index=False)
        rows = ["| graph | Δ | GAPBS iterations | ours phases | ours / GAPBS |", "|---|---:|---:|---:|---:|"]
        for r in it.itertuples():
            rows.append(f"| {r.graph} | {r.delta} | {r.gapbs_iterations} | {r.ours_phases} | "
                        f"{r.ours_phases / r.gapbs_iterations:.1f}× |")
        text += ("\nSynchronised rounds at the best Δ, t=12, first source (GAPBS `-l`; ours: `phases`).\n\n"
                 + "\n".join(rows) + "\n")
    (res / "e4_summary.md").write_text(text)


def save(fig, res: Path, name: str):
    (res / "plots").mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(res / "plots" / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_bars(s: pd.DataFrame, res: Path):
    b = s[s.best_delta]
    graphs = [g for g in GRAPHS if g in set(b.graph)]
    ncol = 4
    nrow = (len(graphs) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.1 * ncol, 2.7 * nrow), squeeze=False)
    w = 0.38
    for ax, g in zip(axes.flat, graphs):
        d = b[b.graph == g].set_index("threads").reindex(THREADS)
        x = range(len(THREADS))
        ax.bar([i - w / 2 - 0.01 for i in x], d.ours_ms, w, color=C_OURS, label="ours (delta-omp)")
        ax.bar([i + w / 2 + 0.01 for i in x], d.gapbs_ms, w, color=C_GAPBS, label="GAPBS")
        top = max(d.ours_ms.max(), d.gapbs_ms.max())
        for i, r in zip(x, d.itertuples()):
            if pd.notna(r.ratio_gapbs_over_ours):
                ax.text(i, max(r.ours_ms, r.gapbs_ms) + 0.03 * top, f"×{r.ratio_gapbs_over_ours:.2f}",
                        ha="center", va="bottom", fontsize=8, color=INK2)
        ax.set_xticks(list(x), [f"t={t}" for t in THREADS])
        ax.set_ylim(0, top * 1.18)
        ax.set_title(f"{g}  (Δ={int(d.delta.dropna().iloc[0])})", loc="left")
        ax.set_ylabel("time (ms)")
        ax.tick_params(axis="x", length=0)
    for ax in axes.flat[len(graphs):]:
        ax.set_visible(False)
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper left", ncol=2, bbox_to_anchor=(0.0, 1.04))
    fig.suptitle("SSSP time at the best Δ: ours vs GAPBS  (label = GAPBS / ours; >1 means ours is faster)",
                 x=0.0, ha="left", y=1.09, fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, res, "e4_bars_best_delta")


def plot_ratio(s: pd.DataFrame, res: Path):
    b = s[s.best_delta]
    graphs = [g for g in GRAPHS if g in set(b.graph)]
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    off = {1: -0.2, 6: 0.0, 12: 0.2}
    for t in THREADS:
        d = b[b.threads == t].set_index("graph").reindex(graphs)
        ax.scatter([i + off[t] for i in range(len(graphs))], d.ratio_gapbs_over_ours, s=42, color=C_T[t],
                   edgecolor=SURFACE, linewidth=1.5, zorder=3, label=f"t={t}")
    ax.axhline(1.0, color=INK2, linewidth=1, zorder=2)
    ax.set_yscale("log", base=2)
    r = b.ratio_gapbs_over_ours.dropna()
    lo = min(0.5, 2 ** math.floor(math.log2(r.min())))
    hi = max(2.0, 2 ** math.ceil(math.log2(r.max())))
    ticks = [2.0 ** k for k in range(int(math.log2(lo)), int(math.log2(hi)) + 1)]
    ax.set_ylim(lo / 1.15, hi * 1.15)
    ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}×"))
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_xlim(-0.6, max(len(graphs), 4) - 0.4)
    ax.set_xticks(range(len(graphs)), graphs)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("GAPBS time / ours time")
    ax.set_title("Above 1: ours faster; below 1: GAPBS faster (best Δ per graph)", loc="left")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout()
    save(fig, res, "e4_ratio_best_delta")


def plot_sweep(res: Path, deltas: pd.DataFrame):
    files = {f.stem: f for f in (res / "sweep").glob("*.csv")}
    graphs = [g for g in GRAPHS if g in files]
    if not graphs:
        return
    ncol = 4
    nrow = (len(graphs) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.1 * ncol, 2.5 * nrow), squeeze=False)
    best = dict(zip(deltas.graph, deltas.best_delta))
    for ax, g in zip(axes.flat, graphs):
        d = pd.read_csv(files[g]).groupby("delta").time_ms.median().reset_index()
        ax.plot(d.delta, d.time_ms, color=C_OURS, linewidth=2, marker="o", markersize=4)
        if g in best:
            bd = d[d.delta == best[g]]
            ax.scatter(bd.delta, bd.time_ms, s=70, color=C_OURS, edgecolor=SURFACE, linewidth=2, zorder=3)
            ax.annotate(f"best Δ={best[g]}", (bd.delta.iloc[0], bd.time_ms.iloc[0]), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=8, color=INK2)
        ax.set_xscale("log", base=2)
        ax.set_ylim(bottom=0)
        ax.set_title(g, loc="left")
        ax.set_xlabel("Δ")
        ax.set_ylabel("time (ms)")
    for ax in axes.flat[len(graphs):]:
        ax.set_visible(False)
    fig.suptitle("Δ sweep of ours (delta-omp), t=12, 1 source, median of 3", x=0.0, ha="left",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, res, "e4_sweep")


def main():
    res = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "results/e4_gapbs")
    runs, deltas = load(res)
    s = summarize(runs, deltas)
    write_tables(s, res)
    plot_bars(s, res)
    plot_ratio(s, res)
    plot_sweep(res, deltas)
    print((res / "e4_summary.md").read_text())


if __name__ == "__main__":
    main()
