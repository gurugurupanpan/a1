# idefix パッケージのDecodeエラー修正版
library("idefix")
set.seed(123)

# コーディングと属性レベルの設定
code  <- c("C","D","D")
c.lvls <- list(c(0,1,2,3,4))

# プロファイルの作成
cs <- Profiles(lvls = c(5,4,3), coding = code, c.lvls = c.lvls)

# 代替案の定数項
alt.cte <- c(0,0,0,1)

# 事前分布の設定
m <- c(-0.3, 1, 0.9, 1.3, 1, 1.4, 0)
v <- diag(c(0.25,0.25,0.25,0.25,0.25,0.25,0.25))

ps <- MASS::mvrnorm(n = 50, mu = m, Sigma = v, empirical = TRUE)
ps <- list(ps[, 1, drop = FALSE], ps[, 2:7])

# デザイン生成
D.nc <- Modfed(
  cand.set = cs,
  n.sets   = 8,
  n.alts   = 4,
  alt.cte  = alt.cte,
  par.draws = ps,
  no.choice = TRUE
)

# レベルのラベル
lvls_labels <- list(
  c("free", "1 EGP", "2 EGP", "3 EGP", "4 EGP"),
  c("Plastic", "Paper", "AWP","AWP-EcoLabel"),
  c("1 kg", "2 kg", "3 kg")
)

# 修正1: D.nc の構造を確認
cat("D.nc の構造:\n")
print(names(D.nc))
cat("\n")

# 修正2: 正しいデザイン行列を取得
# Modfed の戻り値は通常 'design' を直接持っている
design_matrix <- if("design" %in% names(D.nc)) {
  D.nc$design
} else if("BestDesign" %in% names(D.nc) && "design" %in% names(D.nc$BestDesign)) {
  D.nc$BestDesign$design
} else {
  stop("デザイン行列が見つかりません。D.nc の構造を確認してください。")
}

cat("デザイン行列の次元:", dim(design_matrix), "\n\n")

# 修正3: Decode の呼び出し
# c.lvls を NULL にするか、正しい形式で渡す
test1 <- Decode(
  des       = design_matrix,
  n.alts    = 4,
  lvl.names = lvls_labels,
  coding    = code,
  alt.cte   = alt.cte,
  c.lvls    = c.lvls,
  no.choice = TRUE  # TRUE または FALSE、位置ではなくフラグとして指定
)

# 結果の表示
cat("デコード結果:\n")
print(head(test1$design))

# 確率との結合
if("probs" %in% names(D.nc)) {
  result <- cbind(
    test1$design,
    probs = as.vector(t(D.nc$probs))
  )
} else if("BestDesign" %in% names(D.nc) && "probs" %in% names(D.nc$BestDesign)) {
  result <- cbind(
    test1$design,
    probs = as.vector(t(D.nc$BestDesign$probs))
  )
} else {
  cat("\n警告: 確率データが見つかりません\n")
  result <- test1$design
}

cat("\n最終結果 (最初の数行):\n")
print(head(result))
