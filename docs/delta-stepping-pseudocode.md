# Δ-Stepping Pseudocode

> Author: Gino

個人筆記，follow up 隊友寫的 delta stepping codes。


## Sequential

```cpp
   F: frontier
   B: buckets
dist: shortest distance array
 dst: destination of i-th edge
  wt: weight of i-th edge


while (還有 bucket 非空) {
  取出編號最小的非空 bucket B_id
  F := B_id
  B_id := emptyset

  for (u : F) {
    if (dist[u] / Δ ≠ id) {
      increment count of stale entries
    }
    else {
      relax(dist[u], beginning index of u's edge in CSR, end index of u's edge in CSR)
    }
  }
}

relax(du, b, e) {
  for (i = b; i < e; i++) {
    v := dst[i], w := wt[i]
    if (dist[v] > du + w) {
      dist[v] = du + w
      vid := (du + w) / Δ
      B_vid.push(v)
    }
  }
}
```


## Sequential (With Heavy-Light Split)


```cpp
   F: frontier
   S: 目前 bucket 中被 expand 過的點，每個點只記一次，之後 relax heavy edges 時使用
   B: buckets
dist: shortest distance array
 dst: destination of i-th edge
  wt: weight of i-th edge


while (還有 bucket 非空 or S 非空) {
	取出編號最小的非空 bucket B_id'

  if (S 非空 and id' ≠ id) {  // id' ≠ id 代表 B_id 被清空了，要 relax heavy edges
    for (u : S) {
      relax(dist[u], light_end(u), off[u+1])
    }
    S := emptyset
    continue
  }

  id := id'
  F := B_id
  B_id := emptyset

  for (u : F) {
    if (dist[u] / Δ ≠ id) {
      increment count of stale entries
    }
    else {
      if (u ∉ S) S.push(u)                    // @trick 用 epoch 來 dedup
      relax(dist[u], off[u], light_end(u))    // 只 relax light edges (w ≤ Δ)
    }
  }
}

light_end(u) := u 的 adjacency（照 weight 排序）中第一條 w > Δ 的 edge index

relax(du, b, e) { 同前 }
```



## OpenMP

```cpp
   T: thread 數 (tid: thread 編號)
 B^t: thread t 自己的 buckets
      (也就是說，同一個 bucket 的內容分散在各 thread 的 B^t_id 裡)
   F: frontier
nexts[t], sizes[t]: thread t 的暫存變數（padded，避免 false sharing）


parallel (T threads) {
  omp for: dist[v] := ∞
  if (tid == 0) { dist[s] := 0; B^0_0.push(s) }

  while (true) {
    // ---- 1. select：算出 global 最小的非空 bucket
    nexts[tid] := B^tid 中編號最小的非空 bucket
    barrier
    id := min over t of nexts[t]   // 每個 thread 各算一次、結果相同
    if (id == NONE) break

    // ---- 2. gather：把每個 thread 的 B^t_id 接起來變成 F
    local := B^tid_id;  B^tid_id := emptyset
    if (Merge) 從 local 刪掉 dist[v] / Δ ≠ id 的 stale entry
    F := gather(local)
    if (|F| == 0) continue    // 沒有 non-stale entries 就跳過，不算一個 phase

    // ---- 3. relax
    parallel_relax(F)
  }
}


gather(local) {   // 每個 thread 都呼叫，回傳合併後的總長度，gather 在做的事情很像 radix sort / CSR 那樣每個 thread 把自己的那段 slice 填上去
  sizes[tid] := |local|
  barrier
  offset := sum of sizes[0 .. tid-1]  // @trick 用 prefix sum 優化
  total  := sum of all sizes
  if (total > 共用陣列容量) single: resize  // 用 single，這裡需要 barrier
  把 local 拷貝到 共用陣列[offset .. offset + |local|)
  local := emptyset
  barrier
  return total
}


parallel_relax(F) {
  omp for schedule(runtime) nowait:  // F 的元素分給各 thread，但這裡可能還是會有 load balancing 的問題，因為每個點的 degree 差異可能很大
  for (u : F) {
    if (dist[u] / Δ ≠ id) {
      increment count of stale entries
      continue
    }
    du := dist[u]
    for (i = off[u]; i < off[u+1]; i++) {
			v := dst[i], nd := du + wt[i]
			if (atomic_min(dist[v], nd) 成功) {  // CAS
				B^tid_(nd / Δ).push(v)             // push 進自己的 bucket (不用 lock)
			}
		}
  }
  barrier                            // phase 結束
  if (tid == 0) 更新 phases / buckets 計數
}
```

## OpenMP (With Heavy-Light Split)

```cpp
   T: thread 數 (tid: thread 編號)
 B^t: thread t 自己的 buckets
      (也就是說，同一個 bucket 的內容分散在各 thread 的 B^t_id 裡)
 S^t: thread t 在目前 bucket expand 過的點，每個點只記一次，bucket 清空時 relax heavy edges 用
   F: frontier
   H: heavy pass 要處理的點（各 thread 的 S^t 接起來），共用陣列
nexts[t], sizes[t], ssizes[t]: thread t 的暫存變數（padded，避免 false sharing）


parallel (T threads) {
  omp for: dist[v] := ∞
  if (tid == 0) { dist[s] := 0; B^0_0.push(s) }
  id := 0

  while (true) {
    // ---- 1. select：算出 global 最小的非空 bucket，並檢查要不要做 heavy pass
    nexts[tid]  := B^tid 中編號最小的非空 bucket
    ssizes[tid] := |S^tid|
    barrier
    id' := min over t of nexts[t]    // 每個 thread 各算一次、結果相同
    s   := sum over t of ssizes[t]   // 全部 thread 的 S 加起來有多少點

    if (s > 0 and id' ≠ id) {        // B_id 被清空了，要 relax heavy edges
      H := gather(S^tid)             // gather 會順便把 S^tid 清空
      parallel_relax_heavy(H)
      continue
    }
    if (id' == NONE) break
    id := id'

    // ---- 2. gather：把每個 thread 的 B^t_id 接起來變成 F
    local := B^tid_id;  B^tid_id := emptyset
    if (Merge) 從 local 刪掉 dist[v] / Δ ≠ id 的 stale entry
    F := gather(local)
    if (|F| == 0) continue    // 沒有 non-stale entries 就跳過，不算一個 phase

    // ---- 3. relax（只 relax light edges）
    parallel_relax_light(F)
  }
}


gather(local) { 同上 }


parallel_relax_light(F) {
  omp for schedule(runtime) nowait:
  for (u : F) {
    du := dist[u]
    if (du / Δ ≠ id) {
      increment count of stale entries
      continue
    }
    if (u ∉ S) S^tid.push(u)  //@trick 用 epoch 來 dedup
                              // 然後 settled_epoch 用 atomic exchange，
                              // 因為 F 裡可能有重複的 u 被不同 thread 拿到
    for (i = off[u]; i < light_end(u); i++) {     // light edges: w ≤ Δ
      v := dst[i], nd := du + wt[i]
      if (atomic_min(dist[v], nd) 成功) {  // CAS
        B^tid_(nd / Δ).push(v)   // note: 可能 push 回 B_id
      }
    }
  }
  barrier
  if (tid == 0) 更新 phases / buckets 計數
}


parallel_relax_heavy(H) {
  omp for schedule(runtime) nowait:
  for (u : H) {            // 不用檢查 stale，H 裡的點 dist 在這輪已經好了
    du := dist[u]
    for (i = light_end(u); i < off[u+1]; i++) {   // heavy edges: w > Δ
      v := dst[i], nd := du + wt[i]
      if (atomic_min(dist[v], nd) 成功) {
        B^tid_(nd / Δ).push(v)        // Remark: 一定 push 進 > id 的 bucket
      }
    }
  }
  barrier
  if (tid == 0) 更新 phases / heavy_passes 計數
}
```

註：目前看下來覺得瓶頸應該是：
1. barrier 的成本
2. 每次 relax 的 load unbalance（但這個應該只有 degree variance 很大的圖例如 social graph / Kronecker graph 才會有）

