# tests

這是測試 Delta Stepping 演算法正確性的 unit tests，sequential 跟 OpenMP 兩個版本都測。

測資放在 `tests/testcase/`，由 `make test` 直接讀取，並與 Dijkstra 對拍。
- `*.in.txt` 是測試用的圖檔，格式如下（`#` 後面是說明，實際檔案裡沒有）：
  ```txt
  TEST       # 測試資料數
  n m s      # 第一筆測資的點數、邊數、起點
  u1 v1 w1   # 有向邊 (u --> v)，權重 w
  ...
  um vm wm
  n m s
  ...
  ```
  點的編號是 `1 ~ n`，邊權是非負整數。
- 測資以兩個檔案為一組：`*.in.txt` 是測資，`*.ans.txt` 是答案。

## run test

```bash
module load pp
run -c 6 -- make test
```

