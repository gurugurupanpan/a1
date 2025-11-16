# idefix Decode エラーの解決方法

## 問題の原因

`Decode()` 関数でエラーが発生する主な原因は以下の3つです:

### 1. `c.lvls` パラメータの形式問題
`c.lvls` は、"C" (Continuous/Effects) コーディングを使用する属性のカスタムレベルを指定します。

**正しい形式:**
```r
# 1番目の属性のみカスタムレベルを使用する場合
c.lvls <- list(c(0,1,2,3,4))
```

### 2. `Modfed()` の戻り値の構造
`Modfed()` 関数の戻り値は、idfix のバージョンによって異なる可能性があります:

**パターン1 (一般的):**
```r
D.nc$design      # デザイン行列
D.nc$error       # エラー値
```

**パターン2 (あなたのコード):**
```r
D.nc$BestDesign$design  # デザイン行列
D.nc$BestDesign$probs   # 確率
```

### 3. `no.choice` パラメータの指定方法
`Decode()` 関数の `no.choice` パラメータは:
- **整数** (1, 2, 3, 4 など): どの選択肢がノーチョイスかを示す位置
- **論理値** (TRUE/FALSE): ノーチョイスオプションの有無

**修正前:**
```r
no.choice = 4  # 4番目がノーチョイス
```

**修正後 (推奨):**
```r
no.choice = TRUE  # ノーチョイスオプションあり
```

## 解決方法

### 方法1: オブジェクト構造を確認してから実行

```r
# D.nc の構造を確認
print(names(D.nc))

# 適切なデザイン行列を取得
if("design" %in% names(D.nc)) {
  design_matrix <- D.nc$design
} else if("BestDesign" %in% names(D.nc)) {
  design_matrix <- D.nc$BestDesign$design
}

# Decode を実行
test1 <- Decode(
  des       = design_matrix,
  n.alts    = 4,
  lvl.names = lvls_labels,
  coding    = code,
  alt.cte   = alt.cte,
  c.lvls    = c.lvls,
  no.choice = TRUE
)
```

### 方法2: シンプルな修正

元のコードで最も可能性が高い修正:

```r
# 修正版
test1 <- Decode(
  des       = D.nc$design,        # BestDesign を削除
  n.alts    = 4,
  lvl.names = lvls_labels,
  coding    = code,
  alt.cte   = alt.cte,
  c.lvls    = c.lvls,
  no.choice = TRUE                # TRUE に変更
)
```

## デバッグ手順

1. **Modfed の戻り値を確認:**
```r
str(D.nc)
names(D.nc)
```

2. **デザイン行列の次元を確認:**
```r
dim(D.nc$design)  # または dim(D.nc$BestDesign$design)
```

3. **Profiles の出力を確認:**
```r
head(cs)
```

4. **パラメータ数を確認:**
```r
# コーディング "C","D","D" で lvls c(5,4,3) の場合
# パラメータ数: (5-1) + (4-1) + (3-1) = 4 + 3 + 2 = 9
# ただし、C コーディングは異なる可能性あり
```

## 修正されたスクリプトの実行

```bash
Rscript fix_idefix_decode.R
```

このスクリプトは:
1. `D.nc` の構造を自動判定
2. 適切なデザイン行列を取得
3. エラーメッセージを表示してデバッグを支援
