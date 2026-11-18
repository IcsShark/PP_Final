# PP_Final


## 進度

- [x] 演算法實作與正確性測試（seq / OpenMP、light/heavy、stale filter）
- [x] 資料集下載與轉換（road: NY / CTR / USA，social: LJ / OK）
- [ ] 實驗（proposal 的 Q1–Q4）

> Note: 在計中工作站上跑任何東西之前，記得 `module load pp`。


## build & test

```bash
module load pp
cd PP_Final
run -c 4 -- make -j4      # build
run -c 6 -- make test     # 正確性測試，詳見 tests/README.md
```

要跑實驗的話，先依照 [`datasets/README.md`](datasets/README.md) 設定 `PP_DATA_DIR`，然後底下有寫怎麽跑。


## datasets

這個 project 正式使用的資料集都在 `datasets/` 下。

關於這部分的說明（包含來源、怎麽使用），詳見 [`datasets/README.md`](datasets/README.md)。


## tests

這是測試演算法正確性的 unit tests。

關於這部分的說明，詳見 [`tests/README.md`](tests/README.md)。


## example

`example/Delta-stepping 逐步演示.html` 是 Claude 生成的 Delta-stepping 演示動畫。

