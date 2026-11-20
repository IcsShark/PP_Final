# E3 SUMMARY：Load imbalance（Q3a）

**Q3a：** 理想 speedup 和實測 speedup 的差距中，有多少是 load imbalance 造成的？OpenMP 的 schedule 能不能把它補回來？

## 實驗設定

| 項目 | 設定 |
|---|---|
| 機器 | cmpt047，所有 job 都用 `run -c 12` 包下整台機器 |
| 圖 | LJ、OK、kron23（有 hub），USA（沒有 hub，當對照組） |
| Δ | LJ 2048、OK 512、kron23 256、USA 32768（選法見下方「異常與注意事項」） |
| variant / filter | all / pop（預設） |
| schedule | static、dynamic,1、dynamic,64、dynamic,256、guided |
| threads | 6、12 |
| timing build | 4 個 source × 3 次重複，取 median |
| stats build | 4 個 source × 1 次，含 phase log。**只用來算 imbalance，不當時間數據** |
| 正確性 | 640 次執行全部 `--verify` 通過（480 次 timing、160 次 stats） |

資料：`summary.csv`、`ideal_speedup.csv`、`worst_phases.csv`。圖在 `plots/`。

---

## 結論

### 1. 最好的 schedule 是哪一個？chunk size 和 static 差多少？

**有 hub 的圖用 `guided`，USA 用 `static`。dynamic 一定要避開 chunk=1 和 chunk=256。** 以下都是 t=12、相對於 static 的時間比：

| 圖 | static (ms) | dynamic,1 | dynamic,64（目前的預設） | dynamic,256 | guided |
|---|---|---|---|---|---|
| LJ | 268 | 1.29× | 0.96× | 1.01× | **0.94×**（251 ms） |
| OK | 587 | 1.19× | 0.95× | 1.02× | **0.93×**（548 ms） |
| kron23 | 484 | 1.09× | 1.04× | 1.13× | **0.98×**（477 ms） |
| USA | **413** | 2.73× | 1.21× | 1.89× | 1.30× |

t=6 的排名幾乎一樣：social 圖上 guided 比 static 快 4–7%；USA 上 static 仍然最快（480 ms），dynamic,1 慢 2.4 倍。

- **dynamic,1 幾乎在每張圖都最慢**（比 static 慢 9% 到 173%）。唯一的例外是 kron23 t=12，那裡 dynamic,256（1.13×）比它（1.09×）更慢。它的 imbalance 最低（約 1.04–1.16），但每領一個點就要做一次共享計數器的 atomic 操作，這個成本比 imbalance 還大。在 USA 上特別明顯，因為 USA 有約 5.5 萬個 phase、每個 phase 只有約 1400 條邊。
- **chunk 太大會讓 thread 分不到工作。** USA 有 98% 的 phase frontier 少於 256×12 個點，74% 少於 64×12 個點（這些 phase 佔全部 edge 的 23.6%）。所以 dynamic,256 在大多數 phase 切出的 chunk 數比 thread 數少，USA t=12 的 edge imbalance 因此高達 3.42，時間是 static 的 1.9 倍。dynamic,64 也有同樣的問題，但比較輕微（imbalance 1.71）。
- **guided** 的 chunk 一開始大、之後漸漸變小，兼顧了「領取次數少」和「尾端平衡」，所以在 social 圖上最好。但在 USA 上，因為 phase 太小，它仍比 static 慢。
- **建議：** 預設的 `dynamic,64` 不是最好的選擇。以 t=12 和 dynamic,64 相比：social 圖建議改用 `guided`（LJ 快 2.3%、OK 快 1.6%、kron23 快 4.9%），road 圖建議用 `static`（USA 快 17%）。

### 2. imbalance 在 social 圖上吃掉多少？USA 是不是接近 1？

| 圖（t=12） | edge imbalance：static / dynamic,64 / guided | 閒置比例：static / dynamic,64 / guided |
|---|---|---|
| LJ | 1.20 / 1.14 / 1.11 | 6.9% / 2.0% / 0.3% |
| OK | 1.16 / 1.09 / 1.08 | 9.1% / 2.3% / 0.5% |
| kron23 | 1.15 / 1.18 / 1.09 | 8.6% / 5.3% / 1.7% |
| USA | **1.12** / 1.71 / 1.21 | 11.6% / 16.3% / 2.5% |

- 「edge imbalance」是用 edges 加權的 `max_thread_edges / (edges/T)`。
- 「閒置比例」是 Σ(max_wait − mean_wait) / 執行時間，用 stats build 量。

**在 social 圖上，imbalance 只吃掉約 1–9% 的時間：** static 約 7–9%，guided 不到 2%。edge 數最多比平均多 8–20%。這遠小於 t=12 時理想 speedup（約 12）和實測之間的差距，所以 **imbalance 不是 Q3 那個差距的主因**。主因要從 barrier 次數、記憶體頻寬和 SMT 去找，那是 E2 和 Q3 其他部分要回答的。

**USA 在合適的 schedule 下確實接近 1**：static 1.07（t=6）和 1.12（t=12），guided 1.15–1.21。它的 imbalance 只有在 dynamic 的 chunk 太大時才變高，原因是 chunk 數不夠（見第 1 點），跟 hub 無關（USA 的 d_max 只有 9）。

static 在 USA 的閒置比例仍有 12–13%，因為每個 phase 只有幾百個點，barrier 本身的成本和 thread 之間的微小時間差就佔了不小比例。

### 3. 要不要做 edge-level load balancing（把 hub 的邊拆給多個 thread）？

**不值得做。** 用 phase log 算兩種理想 speedup（k=12，用 dynamic,64 t=12 的 log、4 個 source 取平均）：

| 圖 | 不考慮 hub | 考慮 hub（hub 不能拆） | hub 造成的上限損失 |
|---|---|---|---|
| LJ | 12.00 | 11.94 | 0.5% |
| OK | 12.00 | 11.95 | 0.4% |
| kron23 | 12.00 | 11.78 | 1.8% |
| USA | 11.95 | 11.93 | 0.2% |

- 即使把 hub 完美拆開，理想 speedup 最多也只多 0.5–1.8%。實測裡，用 guided 時能被平衡掉的閒置時間也只剩 0.3–1.7%。edge-level balancing 能拿回來的上限就是這麼多，卻要多加一層「拆 edge」的工作分配和同步成本。
- **最差的 phase 確實和 hub 有關：** `worst_phases.csv` 裡，LJ 最差的 phase 中，`max_vertex_edges` 有好幾個正好等於第 1 大 hub 的 degree（20292）；kron23 的最大 hub（152530）在一個 phase 佔了 13% 的邊。但這些 phase 只佔總工作的一小部分，所以加權後的影響不大。
- **kron23 有幾個 phase 的 imbalance 剛好等於 12（= T）。** 這些 phase 的 frontier 只有 55–67 個點，dynamic,64 一個 chunk 就裝完整個 frontier，等於一個 thread 做完全部。這是 chunk size 的問題，不是 hub 的問題，換成 guided 就能避免。

---

## 異常與注意事項

- **Δ 的選法。** main 上還沒有 E1 的結果，所以照 spec 用便宜的 sweep 選 Δ：t=12、1 個 source、1 次重複，取最快的 Δ（`delta_sweep.csv`、`plots/e3_delta_sweep.*`）。
  - LJ 在 1024–8192 之間時間幾乎一樣（256–306 ms），選到的 2048 和 E0 的參考值 512 差異在雜訊範圍內。
  - **USA 選到 32768，和 E0 的參考值 1024 差很多。** 但 sweep 顯示 USA 從 1024（917 ms）到 32768（492 ms）一路變快，這個結果可信。建議和 E1 的結果交叉確認。
  - **Δ 不同時，phase 數會差很多**（USA 的 Δ=1024 約 15 萬個 phase，Δ=32768 約 5 萬個），E3 的結論都是在各圖選定的 Δ 下成立的。
- **SMT 無法觀察。** VM 的 lscpu 顯示 12 cores × 1 thread，看不出哪些 logical CPU 是同一顆實體核心的 SMT 兄弟，也沒有設定 `OMP_PROC_BIND` / `OMP_PLACES`。在 kron23 和 USA 上，dynamic 的 t=12 常常和 t=6 一樣甚至更慢，可能就和 SMT 配置有關。
- **閒置比例取自 stats build。** stats build 比 timing build 慢 0–25%，所以閒置比例的分母是 stats build 的時間，只能拿來比較相對大小。
- **t=12 對 t=6 的加速很小**（LJ 11%、OK 3–6%、kron23 ±3%、USA static 14%），符合 H3 對 SMT 的預期。E2 會更完整地回答這個問題。
- **分析是在工作站外跑的。** 工作站的 Python 沒有 numpy，所以 `analysis/e3_imbalance.py` 在工作站外執行，輸入是這個資料夾裡的 CSV 和 phase log（細節見 META.txt）。

## 檔案

| 檔案 | 內容 |
|---|---|
| `timing.csv` / `stats.csv` | 原始數據，每次執行一列 |
| `summary.csv` | 每張圖 × schedule × threads：時間、vs_static、imbalance、閒置比例 |
| `ideal_speedup.csv` | k = 1..12 的兩種理想 speedup |
| `worst_phases.csv` | 最不平衡的 phase，以及它們是否和 hub 有關 |
| `hub_degrees.csv` | 每張圖 degree 前 50 大的點 |
| `delta.csv` / `delta_sweep.csv` | Δ 選擇 |
| `plots/e3_time_by_sched` | 時間 |
| `plots/e3_imbalance_by_sched` | imbalance |
| `plots/e3_idle_ratio_by_sched` | 閒置比例 |
| `plots/e3_ideal_speedup` | 理想 speedup |
| `plots/e3_phase_imbalance_scatter` | 每個 phase 的 imbalance 對 phase 大小 |
| `plots/e3_delta_sweep` | Δ sweep |
| `META.txt` / `hosts.log` / `code_change.patch` / `check_fields.txt` | 可重現性資訊 |
| `phase_logs/*.csv.gz`（約 37 MB） | 只留在工作站上，不 commit |
