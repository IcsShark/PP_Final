`delta-stepping-serial.cpp` 是手搓的 toy serial Delta-stepping algorithm。

- 編譯並執行：
  ```bash
  g++ -std=c++20 -O2 -o a.out && ./a.out {Delta} < {input_file} && diff {input_file} {correct_output}
  ```
  - `Delta` 是一個整數（Delta-stepping 的 Δ）
  - `input_file` 是測試用的圖檔，跟論文使用的正式格式不同，是簡單的 txt 檔，格式如下：
    ```txt
    TEST       # 測試資料數
    n m s      # 第一筆測資點的數量、邊的數量、起點
    u1 v1 w1   # 有向邊 (u --> v)，權重 w
    u2 v2 w2
    ...
    um vm wm
    n m s
    ...
    ```
    這個資料夾已經有兩個圖檔：`dense.in`、`sparse.in`，`dense.in` 共 11 張圖都是稠密圖，`sparse.in` 共 20 張圖都是稀疏圖。
  - `correct_output` 是對應圖檔的正確答案，格式是「每列代表起點 `s` 到 `1 ~ n` 各點的最短距離」。`dense.in` 對應的 `correct_output` 是 `dense.ac`，`sparse.in` 則是 `sparse.ac`。

`Delta-stepping 逐步演示.html` 是 Claude 生成的 Delta-stepping algorithm 的演示動畫。

