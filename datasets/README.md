# Project Datasets

這個 project 正式使用的 graph datasets。

- 來源、檢查結果見 [`SOURCES.md`](SOURCES.md)
- MD5 Checksum 見 [`md5sums.txt`](md5sums.txt)

## Datasets 怎麽抓

### 在計中的工作站

處理好的圖檔資料已經放在共用目錄 `/u/cs/111/111550055/pp_data`，設定環境變數即可：

```tcsh
# tcsh / csh
setenv PP_DATA_DIR /u/cs/111/111550055/pp_data
```
```bash
# bash / zsh
export PP_DATA_DIR=/u/cs/111/111550055/pp_data
```
```fish
# fish
set -gx PP_DATA_DIR /u/cs/111/111550055/pp_data
```

使用方式參考 [Run](#run)。

> Note：放在 `/u/cs/111/111550055/pp_data` 是因為我暫時想不到更好的地方

### 在其他機器

在 repo root 執行：
```bash
bash scripts/fetch-datasets.sh              # 下載 raw 圖檔、驗證 md5
                                              並放到 $PP_DATA_DIR/raw/
bash scripts/convert-all.sh                 # build bin/convert、將 raw 圖檔轉成 CSR
                                              並放到 $PP_DATA_DIR/csr/
```

`$PP_DATA_DIR`：沒設定這個環境變數時，預設放在 repo 內的 `datasets/raw`、`datasets/csr`（均已加進 `.gitignore`）。

## Run

```bash
run -c 6 -- ./bin/sssp -g $PP_DATA_DIR/csr/NY.csr -t 1,6 --verify
```

