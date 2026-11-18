# E4：GAPBS baseline 結果

ours = `bin/sssp -a delta-omp`（`--variant all --filter pop --sched dynamic,64`），GAPBS = `sssp`（commit `941462c`）。
兩邊跑的是同一張圖、同一組權重、同一組 4 個起點、同一個 Δ、同樣的 thread 數，而且在同一個 job（同一台 node、同一時段，`run -c 12`）裡先後執行。
時間 = 每個起點 3 次 trial 取 median，再對 4 個起點取平均；不含讀圖、含 dist 初始化（兩邊一致）。
所有 run 都通過驗證：ours 每次都和 Dijkstra 比對（`--verify`），GAPBS 每個 trial 都 `Verification: PASS`。
完整數字見 [`e4_summary.md`](e4_summary.md) / [`e4_summary.csv`](e4_summary.csv)，執行環境與指令見 [`META.txt`](META.txt)。

## 結論

- **GAPBS 在 8 張圖、所有 thread 數都比較快。** GAPBS / ours 時間比的幾何平均：t=1 是 0.73，t=6 是 0.62，t=12 是 0.56，也就是 ours 慢 1.4×、1.6×、1.8×。
- **差距最大的是路網，而且 thread 越多越大**：t=12 時 ours 在 NY / CTR / USA 慢 2.9× / 2.1× / 2.4×。差距最小的是 kron23 和 urand23（慢 1.2–1.25×）。
- **路網的主因是同步次數**：在最佳 Δ、t=12 下，ours 的 phase 數是 GAPBS iteration 數的約 40 倍（grid2896 是 15 倍），社群圖和合成圖只有 1.1–2.2 倍。GAPBS 的 bucket fusion 讓小 bucket 不必經過 barrier。
- **單執行緒也慢**：t=1 時 ours 仍慢 1.2–1.5×，表示除了同步，循序效率（資料寬度與記憶體布局）也有差。
- **擴展性**：t=1 → t=12 的加速，ours 是 2.2–4.3×，GAPBS 是 3.4–5.4×。從 t=6 到 t=12（多出的是 SMT 執行緒），ours 只快 0–16%，GAPBS 在路網、OK、grid 上還能快 21–41%。

## 關鍵數字（每張圖的最佳 Δ）

| 圖 | Δ | t=1 ours / GAPBS (ms) | t=6 ours / GAPBS (ms) | t=12 ours / GAPBS (ms) | GAPBS / ours（t=1, 6, 12） |
|---|---:|---:|---:|---:|---|
| NY | 32768 | 18.6 / 12.5 | 8.8 / 3.6 | 8.5 / 2.9 | 0.67, 0.40, 0.34 |
| CTR | 32768 | 1034 / 735 | 327 / 176 | 308 / 145 | 0.71, 0.54, 0.47 |
| USA | 32768 | 1513 / 1050 | 520 / 246 | 495 / 201 | 0.69, 0.47, 0.41 |
| LJ | 4096 | 1132 / 854 | 303 / 207 | 267 / 177 | 0.75, 0.68, 0.66 |
| OK | 1024 | 2370 / 1617 | 589 / 380 | 555 / 302 | 0.68, 0.65, 0.54 |
| kron23 | 256 | 1774 / 1444 | 500 / 440 | 500 / 422 | 0.81, 0.88, 0.84 |
| urand23 | 2048 | 3384 / 2567 | 928 / 750 | 866 / 696 | 0.76, 0.81, 0.80 |
| grid2896 | 524288 | 616 / 463 | 170 / 123 | 146 / 87 | 0.75, 0.72, 0.59 |

圖：[`plots/e4_bars_best_delta`](plots/e4_bars_best_delta.png)（長條圖）、[`plots/e4_ratio_best_delta`](plots/e4_ratio_best_delta.png)（比值）、[`plots/e4_sweep`](plots/e4_sweep.png)（Δ sweep）。

## 同步輪數（最佳 Δ、t=12、第一個起點）

| 圖 | GAPBS iterations | ours phases | ours / GAPBS |
|---|---:|---:|---:|
| NY | 31 | 1306 | 42× |
| CTR | 723 | 28972 | 40× |
| USA | 1367 | 52475 | 38× |
| LJ | 272 | 598 | 2.2× |
| OK | 396 | 579 | 1.5× |
| kron23 | 1968 | 2190 | 1.1× |
| urand23 | 249 | 521 | 2.1× |
| grid2896 | 562 | 8547 | 15× |

GAPBS 每個 iteration 有 2 個 barrier；ours 每個 phase 約 4 個（select、gather 兩個、relax 結束）。輪數差越多的圖，t=12 的差距也越大（路網 > grid > 社群 / 合成圖），符合「路網的差距主要來自同步」的解釋。

## GAPBS 建議的 Δ（spec 4.5）

GAPBS 的 `benchmark/bench.mk` 對 road graph 用 `-d50000`。對 kron / urand 用的 `-d2` 是配合 GAPBS 自己產生器的權重（1–255），不適用於我們 [1, 2^18) 的權重，所以只在 NY / CTR / USA 上跑。
Δ=50000 落在我們 sweep 的 32768 和 65536 之間。GAPBS 在 Δ=50000 下比在我們的最佳 Δ（32768）慢 6–35%（例：USA t=12 是 221 vs 201 ms，NY t=6 是 4.8 vs 3.6 ms），所以**我們的最佳 Δ 對 GAPBS 也適用，甚至更好**。ours 在 Δ=50000 下則和最佳 Δ 差不多或稍慢（NY t=6/12 幾乎一樣，t=1 慢 21%；CTR / USA 慢 3–12%）。

## 實作差異（ours `src/delta_omp.cpp` vs GAPBS `src/sssp.cc`）

| 面向 | ours | GAPBS |
|---|---|---|
| bucket 怎麼存 | 每個 thread 一個 `RingBins`：floor(w_max/Δ)+2 格的環狀視窗 + overflow list，用 occupancy bitmap 找下一個非空 bucket | 每個 thread 一個 `vector<vector<NodeID>>`，用 bucket 編號直接索引，不夠就 resize |
| frontier 怎麼組 | 各 thread 回報大小 → barrier → prefix sum 算 offset → 拷貝進共用陣列 → barrier（需要時 `single` resize） | 各 thread 用 `fetch_and_add` 在共用 tail 上搶位置後拷貝；frontier 一開始就配 m 格，不需 resize |
| 選下一個 bucket | 各 thread 寫自己的 padded 欄位 → barrier → 每個 thread 各自算 min | `omp critical` 更新共用的 next_bin_index → barrier |
| light / heavy | 有實作（`--variant lh`），E4 用 `all` | 沒有，一律 relax 全部的邊 |
| **bucket fusion** | 沒有：重新放進目前 bucket 的點要等下一個 phase（又是一輪 barrier） | 有：本地的目前 bucket 少於 1000 個點時，thread 自己繼續處理，不經過 barrier（Zhang et al., CGO'20） |
| 每輪同步 | 約 4 個 barrier / phase | 2 個 barrier / iteration |
| stale 判斷 | `dist[u] / Δ ≠ cur` 就跳過 | `dist[u] < Δ·cur` 就跳過（效果相同） |
| 資料寬度 | dist 是 `uint64`（8 B）；邊是 SoA：`dst[]`、`wt[]` 各 4 B | dist 是 `int32`（4 B）；邊是 AoS：`(v, w)` 連在一起，8 B |
| 排程 / relax | `schedule(dynamic,64)`；CAS 迴圈的 atomic_min | `schedule(dynamic,64)`；CAS 迴圈 |
| 編譯 | `-O3 -march=native` | `-O3`（沒有 `-march=native`） |

**為什麼 GAPBS 比較快：**
1. **高直徑的圖（路網、grid）主要差在同步。** 每個 bucket 裡的 frontier 很小，ours 每多一輪就多約 4 個 barrier。GAPBS 靠 bucket fusion 把輪數壓到 1/15–1/40，所以 thread 越多（barrier 越貴），差距越大。
2. **低直徑的圖（LJ、OK、kron23、urand23）輪數差不多，差距主要來自循序效率**（t=1 就慢 1.2–1.5×）。以下是根據程式碼的推測，還沒有實驗驗證：dist 用 8 B 讓 `dist[v]` 的隨機存取多一倍的 cache 用量。例如 OK 的 dist 陣列，ours 是 24.6 MB、GAPBS 是 12.3 MB，而 L3 只有 12 MB（spec；`lscpu` 顯示 16 MiB）。另外 SoA 每條邊要讀兩條資料流，GAPBS 的 AoS 只要一條。
3. 編譯參數對 ours 比較有利（`-march=native`），但 GAPBS 還是比較快，所以差距不是編譯參數造成的。

**可以接著做的實驗（給團隊參考）：** 在 ours 加上 bucket fusion，預期路網的差距最明顯縮小；把 dist 改成 32-bit，或把邊改成 AoS，可以驗證第 2 點的推測。

## 異常與注意事項

1. **共用的參考檔 `csr/LJ.csr` 壞了一小段。** 用 md5 相同的原始檔、照 `convert-all.sh` 重建，有 20 個點（約 600 條邊）不同，而且參考檔裡有 18 條重複邊，這是 `build_csr` 不可能產生的。其他 7 張圖都完全相同（見 [`ref_check.log`](ref_check.log)，由 `scripts/exp/e4_check_ref.sh` 產生）。經使用者決定，**E4 的 LJ 兩邊都用重建的版本**，所以和 E0–E2 用的 LJ 有 0.001% 的邊不同，對時間的影響可以忽略。建議參考檔的擁有者重新產生 LJ.csr。
2. **E0 的參考 Δ 和 sweep 結果差很多**：NY 256 vs 32768、CTR 512 vs 32768、USA 1024 vs 32768、LJ 512 vs 4096（t=12 的 sweep）。例如 NY 用 256 比用 32768 慢約 3 倍。建議確認 E0 校準時的條件。
3. **grid2896 的最佳 Δ（524288）大於最大邊權（262143）**，在預設 sweep 範圍 2^6–2^18 的邊界外，所以只對 grid2896 把 sweep 延伸到 2^24。
4. **兩邊的最佳 Δ 不一定相同**：我們用 ours 的最佳 Δ 和它前後兩個值跑兩邊。在這 3 個 Δ 裡，GAPBS 有時在相鄰的 Δ 最快（例如 NY、USA t=12 是 16384），所以表中 GAPBS 的數字可能還不是它的最佳值，結論不受影響。
5. **GAPBS 第一個 trial 常常比較慢**（warm-up，例如 OK t=12 的一個起點：422 → 311 → 323 ms），取 median 已經排除。
6. **硬體**：job 分散在 9 台 compute node（cmpt047–099），都是 i5-10500、12 CPU、11.9 GB（抽查 cmpt048、cmpt051 的 `lscpu`）。比值都是同一個 job 內的比較，不受 node 差異影響。
7. **執行過程的問題（不影響結果）**：
   - home 的 quota（10 GB）滿了一次，USA 的 sweep 結果寫入失敗；之後重跑了，並在每一步都加上檔案大小和列數檢查。
   - 有一次在 job 執行中同步腳本，造成 `Stale file handle`，OK 的 prep 因此重跑。

## 檔案

```
scripts/exp/e4_env.sh          共用設定與 driver 用的函式
scripts/exp/e4_prep.sh         重建圖、cmp、轉成 GAPBS .wsg（含大小檢查）
scripts/exp/e4_sweep.sh        Δ sweep（ours，t=12）
scripts/exp/e4_pick_delta.sh   挑最佳 Δ 和前後兩個值
scripts/exp/e4_run.sh          同一個 job 裡跑 ours 和 GAPBS
scripts/exp/e4_iters.sh        GAPBS iteration 數（-l）
scripts/exp/e4_all.sh          driver（login node，一次送一個 job）
scripts/exp/e4_suggested.sh    spec 4.5：Δ=50000
scripts/exp/e4_check_ref.sh    重建並比對參考 CSR（+ e4_csrdiff.cpp）
scripts/exp/e4_meta.sh         產生 META.txt
analysis/e4_gapbs.py           表格與圖（uv run analysis/e4_gapbs.py）
results/e4_gapbs/
  raw/*.ours.csv, *.gapbs.csv  每個 (圖, t, Δ) 一組，每列一個 rep / trial
  deltas.csv, sweep/, iters/   Δ 的選擇、sweep 原始資料、iteration 數
  e4_summary.{csv,md}, e4_iters.csv
  plots/*.{pdf,png}
  logs/                        每個 job 的完整輸出（含 GAPBS 原始輸出）與 driver.log
  META.txt, ref_check.log
```
