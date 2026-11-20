#!/usr/bin/env python3
"""E3 analysis: load imbalance (Q3a). See experiment/E3-experiment-spec.md section 6.

  python3 analysis/e3_imbalance.py [results/e3_imbalance]

Inputs (written by scripts/exp/e3_*.sh):
  timing.csv             timing build, 4 sources x 3 reps per (graph, sched, threads)
  stats.csv              stats build, 4 sources x 1 rep (NOT used as timing data)
  phase_logs/phases_<graph>_<sched>.csv.gz   per-phase records of the stats runs
  hub_degrees.csv        top out-degrees per graph
  delta.csv, delta_sweep.csv

Outputs (same directory):
  summary.csv            per graph x sched x threads: time, imbalance, idle ratio
  ideal_speedup.csv      per graph x k: ideal speedup without / with the hub bound
  worst_phases.csv       most imbalanced phases per graph, with hub check
  plots/e3_*.pdf|png

Definitions (shared with E2 — keep them identical):
  per-phase imbalance  = max_thread_edges / (edges / T)            (1.0 = balanced)
  weighted imbalance   = sum_p edges_p * imb_p / sum_p edges_p = T * sum max_thread_edges / sum edges
  idle ratio           = sum_p (max_wait_p - mean_wait_p) / total run time
  ideal, no hub bound  : T_k = sum_p ceil(edges_p / k)
  ideal, hub bound     : T_k = sum_p max(ceil(edges_p / k), max_vertex_edges_p)
  ideal speedup        = T_1 / T_k with T_1 = sum_p edges_p
"""
import glob
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(REPO, "results", "e3_imbalance")
PLOTS = os.path.join(RES, "plots")

GRAPHS = ["LJ", "OK", "kron23", "USA"]
SCHEDS = ["static", "dynamic:1", "dynamic:64", "dynamic:256", "guided"]  # CSV writes ',' as ':'
THREADS = [6, 12]
REF = ("dynamic:64", 12)  # reference config for per-phase plots / ideal speedup
COLORS = {6: "#4C72B0", 12: "#DD8452"}


def savefig(fig, name):
    os.makedirs(PLOTS, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(PLOTS, f"{name}.{ext}"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def load_phase_logs():
    frames = []
    for path in sorted(glob.glob(os.path.join(RES, "phase_logs", "phases_*.csv.gz"))):
        tag = os.path.basename(path)[len("phases_"):-len(".csv.gz")]
        graph = next(g for g in GRAPHS if tag.startswith(g + "_"))
        sched = tag[len(graph) + 1:].replace("_", ":")
        df = pd.read_csv(path)
        df["sched"] = sched
        frames.append(df)
    if not frames:
        sys.exit("no phase logs found in " + os.path.join(RES, "phase_logs"))
    return pd.concat(frames, ignore_index=True)


def check_inputs(timing, stats):
    for name, df in (("timing", timing), ("stats", stats)):
        bad = df[df["verified"] != 1]
        if len(bad):
            sys.exit(f"{name}.csv has {len(bad)} runs that are not verified=1; stop and report (spec rule)")
    exp = len(GRAPHS) * len(SCHEDS) * len(THREADS)
    for name, df, per in (("timing", timing, 12), ("stats", stats, 4)):
        got = df.groupby(["graph", "sched", "threads"]).size()
        if len(got) != exp or (got != per).any():
            print(f"WARNING: {name}.csv has {len(got)} configs (expected {exp}) / runs per config {sorted(set(got))}")


def per_run_phase_metrics(ph, stats):
    """One row per stats run: weighted imbalance and idle ratio."""
    ph = ph[ph["edges"] > 0]
    g = ph.groupby(["graph", "sched", "threads", "source"])
    out = g.agg(edges=("edges", "sum"), mte=("max_thread_edges", "sum"), phases=("phase", "size"),
                idle_us=("max_wait_us", "sum"), mean_wait_us=("mean_wait_us", "sum")).reset_index()
    idle = (ph["max_wait_us"] - ph["mean_wait_us"]).groupby([ph[c] for c in ["graph", "sched", "threads", "source"]]).sum()
    out = out.merge(idle.rename("idle_gap_us").reset_index(), on=["graph", "sched", "threads", "source"])
    out["imbalance"] = out["threads"] * out["mte"] / out["edges"]
    st = stats[["graph", "sched", "threads", "source", "time_ms"]].rename(columns={"time_ms": "stats_time_ms"})
    out = out.merge(st, on=["graph", "sched", "threads", "source"], how="left")
    out["idle_ratio"] = out["idle_gap_us"] / (out["stats_time_ms"] * 1e3)
    out["mean_wait_ratio"] = out["mean_wait_us"] / (out["stats_time_ms"] * 1e3)
    return out


def ideal_speedups(ph):
    ref = ph[(ph["sched"] == REF[0]) & (ph["threads"] == REF[1]) & (ph["edges"] > 0)]
    rows = []
    for (graph, src), d in ref.groupby(["graph", "source"]):
        e = d["edges"].to_numpy(dtype=np.int64)
        mv = d["max_vertex_edges"].to_numpy(dtype=np.int64)
        t1 = e.sum()
        for k in range(1, 13):
            nohub = np.ceil(e / k).sum()
            hub = np.maximum(np.ceil(e / k), mv).sum()
            rows.append(dict(graph=graph, source=src, k=k, ideal_nohub=t1 / nohub, ideal_hub=t1 / hub))
    df = pd.DataFrame(rows)
    return df.groupby(["graph", "k"], as_index=False)[["ideal_nohub", "ideal_hub"]].mean()


def worst_phases(ph, hubs, top=8):
    ref = ph[(ph["sched"] == REF[0]) & (ph["threads"] == REF[1]) & (ph["edges"] > 0)].copy()
    ref["imbalance"] = ref["max_thread_edges"] / (ref["edges"] / ref["threads"])
    ref["excess_edges"] = ref["max_thread_edges"] - ref["edges"] / ref["threads"]  # work the slowest thread did beyond its fair share
    rows = []
    for graph, d in ref.groupby("graph"):
        hd = hubs[hubs["graph"] == graph]
        deg_rank = {int(r.degree): int(r.rank) for r in hd.itertuples()}
        for r in d.nlargest(top, "excess_edges").itertuples():
            rank = deg_rank.get(int(r.max_vertex_edges))
            rows.append(dict(graph=graph, source=r.source, phase=r.phase, bucket=r.bucket, edges=r.edges,
                             frontier=r.frontier, max_thread_edges=r.max_thread_edges,
                             max_vertex_edges=r.max_vertex_edges, imbalance=round(r.imbalance, 3),
                             share_of_phase=round(r.max_vertex_edges / r.edges, 3),
                             is_top50_hub_degree=rank is not None, hub_rank=rank if rank else ""))
    return pd.DataFrame(rows)


def plot_bars(summary, col, ylabel, name, title, ref_line=None, err=None):
    fig, axes = plt.subplots(1, len(GRAPHS), figsize=(4.2 * len(GRAPHS), 3.6), squeeze=False)
    x = np.arange(len(SCHEDS))
    for ax, graph in zip(axes[0], GRAPHS):
        d = summary[summary["graph"] == graph]
        for i, t in enumerate(THREADS):
            dt = d[d["threads"] == t].set_index("sched").reindex(SCHEDS)
            yerr = None
            if err:
                yerr = np.vstack([(dt[col] - dt[err[0]]).to_numpy(dtype=float), (dt[err[1]] - dt[col]).to_numpy(dtype=float)]).clip(min=0)
            ax.bar(x + (i - 0.5) * 0.38, dt[col].to_numpy(dtype=float), 0.38, yerr=yerr, capsize=2, color=COLORS[t], label=f"t={t}")
        if ref_line is not None:
            ax.axhline(ref_line, color="gray", lw=0.8, ls="--")
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace("dynamic:", "dyn,") for s in SCHEDS], rotation=30, ha="right")
        ax.set_title(graph)
        ax.grid(axis="y", alpha=0.3)
    axes[0][0].set_ylabel(ylabel)
    axes[0][-1].legend()
    fig.suptitle(title)
    fig.tight_layout()
    savefig(fig, name)


def main():
    timing = pd.read_csv(os.path.join(RES, "timing.csv"))
    stats = pd.read_csv(os.path.join(RES, "stats.csv"))
    hubs = pd.read_csv(os.path.join(RES, "hub_degrees.csv"))
    deltas = pd.read_csv(os.path.join(RES, "delta.csv"))
    check_inputs(timing, stats)
    ph = load_phase_logs()

    # 1. time (timing build): median over 4 sources x 3 reps, with IQR
    tg = timing.groupby(["graph", "sched", "threads"])["time_ms"]
    summary = tg.median().rename("time_ms").to_frame()
    summary["time_p25"] = tg.quantile(0.25)
    summary["time_p75"] = tg.quantile(0.75)
    summary["runs"] = tg.size()
    summary = summary.reset_index()
    best_static = summary[summary["sched"] == "static"].set_index(["graph", "threads"])["time_ms"]
    summary["vs_static"] = summary.apply(lambda r: r["time_ms"] / best_static[(r["graph"], r["threads"])], axis=1)

    # 2./3. imbalance and idle ratio (stats build, averaged over sources)
    pr = per_run_phase_metrics(ph, stats)
    agg = pr.groupby(["graph", "sched", "threads"]).agg(
        imbalance=("imbalance", "mean"), idle_ratio=("idle_ratio", "mean"),
        mean_wait_ratio=("mean_wait_ratio", "mean"), phases=("phases", "mean"),
        stats_time_ms=("stats_time_ms", "median")).reset_index()
    summary = summary.merge(agg, on=["graph", "sched", "threads"], how="left")
    summary = summary.merge(deltas[["graph", "delta"]], on="graph")
    summary["graph"] = pd.Categorical(summary["graph"], GRAPHS)
    summary["sched"] = pd.Categorical(summary["sched"], SCHEDS)
    summary = summary.sort_values(["graph", "threads", "sched"])
    summary.round(4).to_csv(os.path.join(RES, "summary.csv"), index=False)

    # 4. ideal speedups
    ideal = ideal_speedups(ph)
    ideal["hub_loss"] = 1 - ideal["ideal_hub"] / ideal["ideal_nohub"]
    ideal.round(4).to_csv(os.path.join(RES, "ideal_speedup.csv"), index=False)

    worst = worst_phases(ph, hubs)
    worst.to_csv(os.path.join(RES, "worst_phases.csv"), index=False)

    # ---------------- plots
    plot_bars(summary, "time_ms", "median time (ms)", "e3_time_by_sched",
              "E3: run time by OpenMP schedule (timing build, median, IQR bars)", err=("time_p25", "time_p75"))
    plot_bars(summary, "imbalance", "edge-weighted max/mean thread edges", "e3_imbalance_by_sched",
              "E3: per-phase edge imbalance (1.0 = perfectly balanced)", ref_line=1.0)
    plot_bars(summary, "idle_ratio", "idle ratio", "e3_idle_ratio_by_sched",
              "E3: barrier idle ratio  sum(max_wait - mean_wait) / run time  (stats build)")

    fig, axes = plt.subplots(1, len(GRAPHS), figsize=(4.2 * len(GRAPHS), 3.4), squeeze=False)
    for ax, graph in zip(axes[0], GRAPHS):
        d = ideal[ideal["graph"] == graph]
        ax.plot(d["k"].to_numpy(), d["k"].to_numpy(), color="gray", lw=0.8, ls=":", label="linear")
        ax.plot(d["k"].to_numpy(), d["ideal_nohub"].to_numpy(), marker="o", ms=3, label="ideal, no hub bound")
        ax.plot(d["k"].to_numpy(), d["ideal_hub"].to_numpy(), marker="s", ms=3, label="ideal, hub bound")
        ax.set_title(graph)
        ax.set_xlabel("threads k")
        ax.grid(alpha=0.3)
    axes[0][0].set_ylabel("ideal speedup (work model)")
    axes[0][-1].legend(fontsize=8)
    fig.suptitle(f"E3: ideal speedup from phase logs ({REF[0].replace(':', ',')}, t={REF[1]} logs)")
    fig.tight_layout()
    savefig(fig, "e3_ideal_speedup")

    fig, axes = plt.subplots(1, len(GRAPHS), figsize=(4.2 * len(GRAPHS), 3.4), squeeze=False)
    ref = ph[(ph["sched"] == REF[0]) & (ph["threads"] == REF[1]) & (ph["edges"] > 0)]
    for ax, graph in zip(axes[0], GRAPHS):
        d = ref[ref["graph"] == graph]
        imb = d["max_thread_edges"] / (d["edges"] / d["threads"])
        ax.scatter(d["edges"].to_numpy(), imb.to_numpy(), s=3, alpha=0.3, color="#4C72B0", rasterized=True)
        ax.set_xscale("log")
        ax.axhline(1.0, color="gray", lw=0.8, ls="--")
        ax.set_title(graph)
        ax.set_xlabel("edges in phase")
        ax.grid(alpha=0.3)
    axes[0][0].set_ylabel("phase imbalance (max/mean)")
    fig.suptitle(f"E3: per-phase imbalance vs phase size ({REF[0].replace(':', ',')}, t={REF[1]}, all 4 sources)")
    fig.tight_layout()
    savefig(fig, "e3_phase_imbalance_scatter")

    sweep_path = os.path.join(RES, "delta_sweep.csv")
    if os.path.exists(sweep_path):
        sw = pd.read_csv(sweep_path)
        fig, ax = plt.subplots(figsize=(5.5, 3.6))
        for graph in GRAPHS:
            d = sw[sw["graph"] == graph].sort_values("delta")
            ax.plot(d["delta"].to_numpy(), d["time_ms"].to_numpy(), marker="o", ms=3, label=graph)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xlabel("delta")
        ax.set_ylabel("time (ms), t=12, 1 source")
        ax.grid(alpha=0.3)
        ax.legend()
        ax.set_title("E3: delta selection sweep")
        fig.tight_layout()
        savefig(fig, "e3_delta_sweep")

    # ---------------- console summary (used to write SUMMARY.md)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 200)
    cols = ["graph", "threads", "sched", "time_ms", "vs_static", "imbalance", "idle_ratio", "mean_wait_ratio", "phases"]
    print(summary[cols].round(3).to_string(index=False))
    print()
    print(ideal[ideal["k"].isin([6, 12])].round(3).to_string(index=False))
    print()
    print(worst.to_string(index=False))
    print("\nwrote", RES)


if __name__ == "__main__":
    main()
