# 盛岡市水田検出システム 2025年版 / Morioka City Paddy Field Detection System 2025

Google Earth Engineを使用して盛岡市中心半径50kmの水田を検出・推定するプロジェクトです。
2025年7月の干ばつ条件を考慮した特別なアルゴリズムを使用しています。

A project to detect and estimate paddy field areas within 50km radius of Morioka City center using Google Earth Engine.
Uses a special drought-aware algorithm accounting for July 2025 drought conditions.

## 概要 / Overview

このプロジェクトは、衛星画像データとGoogle Earth Engine (GEE) APIを使用して、盛岡市中心から半径50km圏内の水田を自動的に識別し、その面積を計算します。

2025年の特別な条件:
- **7月の干ばつ**: 通常より低いNDVI閾値を使用
- **農地構成**: 盛岡市・岩手県の農地の約60%が水田であることを考慮

This project uses satellite imagery data and the Google Earth Engine (GEE) API to automatically identify rice paddy fields within a 50km radius of Morioka City center and calculate their total area.

Special conditions for 2025:
- **July drought**: Uses lower NDVI thresholds than normal
- **Agricultural composition**: Considers that approximately 60% of agricultural land in Morioka/Iwate is paddy fields

## 対象地域 / Target Region

- **中心地点**: 盛岡市役所 (39.7036°N, 141.1527°E)
- **範囲**: 中心から半径50km
- **総面積**: 約7,854 km² (円形範囲)

- **Center Point**: Morioka City Hall (39.7036°N, 141.1527°E)
- **Range**: 50km radius from center
- **Total Area**: Approximately 7,854 km² (circular region)

## 手法 / Methodology

### 1. 使用する衛星データ / Satellite Data Used

- **Sentinel-2 (光学)**:
  - 10m解像度のマルチスペクトル画像
  - NDVI, NDWI, LSWI, EVIを計算
- **Sentinel-1 (SAR)**:
  - VV/VH偏波
  - 田植え期の湛水検出に使用

### 2. 時系列解析 / Time Series Analysis

水田の季節変動パターンを5つの期間に分けて解析:

1. **田植え期** (5月中旬〜6月中旬)
   - 低いNDVI (< 0.3)
   - 高いNDWI/LSWI (湛水状態)
   - SAR VV低値 (水面反射)

2. **初期生育期** (6月下旬)
   - NDVIの上昇開始

3. **干ばつ期** (7月) ⚠️ **重要**
   - 通常: NDVI > 0.6 (健全な稲)
   - 2025年干ばつ: NDVI 0.3〜0.7 (閾値を調整)
   - EVI使用で感度向上

4. **回復期** (8月)
   - NDVI > 0.35 (干ばつからの回復)
   - EVI > 0.3

5. **収穫前期** (9月)
   - NDVI 0.3〜0.65 (成熟期)

### 3. 干ばつ考慮アルゴリズム / Drought-Aware Algorithm

2025年7月の干ばつに対応するため、以下の調整を実施:

- 7月のNDVI閾値を0.6から0.3〜0.7に緩和
- EVI (Enhanced Vegetation Index) を追加して感度向上
- SAR画像による湛水期の確認を重視
- 複数期間の総合判定で誤検出を防止

To handle the July 2025 drought, the following adjustments were made:

- Relaxed July NDVI threshold from 0.6 to 0.3-0.7
- Added EVI (Enhanced Vegetation Index) for improved sensitivity
- Emphasized SAR-based flooding period detection
- Multi-period comprehensive determination to prevent false positives

### 4. 面積推定 / Area Estimation

- 検出された水田面積を直接計算
- 水田が農地の60%という統計情報から総農地面積を推定
- その他の農地面積(畑、果樹園等)も算出

## 必要な環境 / Requirements

- Python 3.7+
- Google Earth Engine account
- 必要なライブラリ:
  - earthengine-api
  - folium (可視化用)
  - numpy

## インストール / Installation

```bash
# リポジトリのクローン / Clone repository
git clone <repository-url>
cd a1

# 依存パッケージのインストール / Install dependencies
pip install -r requirements.txt

# Google Earth Engineの認証 / Authenticate Google Earth Engine
earthengine authenticate
```

## 使用方法 / Usage

### 1. Pythonスクリプトで面積計算 / Calculate Area with Python Script

```bash
python morioka_paddy_detection_2025.py
```

出力例 / Example Output:
```
検出された水田面積 / Detected Paddy Field Area:
  XX,XXX.XX ヘクタール / hectares
  XXX.XX 平方キロメートル / km²

推定総農地面積 / Estimated Total Agricultural Area:
  (水田が農地の60%と仮定)
  XX,XXX.XX ヘクタール / hectares
```

### 2. 結果の可視化 / Visualize Results

```bash
python visualize_morioka_2025.py
```

インタラクティブなHTMLマップが生成されます:
- `morioka_paddy_map_2025.html`

An interactive HTML map will be generated:
- `morioka_paddy_map_2025.html`

### 3. Google Earth Engine Code Editorで実行 / Run in GEE Code Editor

1. https://code.earthengine.google.com/ にアクセス
2. `morioka_paddy_detection_2025.js` の内容をコピー
3. スクリプトを実行
4. マップ上で結果を確認

1. Access https://code.earthengine.google.com/
2. Copy contents of `morioka_paddy_detection_2025.js`
3. Run the script
4. View results on the map

## ファイル構成 / File Structure

```
.
├── morioka_paddy_detection_2025.py    # メイン検出スクリプト (Python)
├── morioka_paddy_detection_2025.js    # GEE Code Editor用スクリプト
├── visualize_morioka_2025.py          # 可視化スクリプト
├── requirements.txt                    # Python依存パッケージ
├── README_MORIOKA_2025.md             # このファイル
│
# 既存ファイル (岩手県全体用)
├── iwate_paddy_detection.py           # 岩手県全体の検出スクリプト
├── iwate_paddy_detection.js           # 岩手県全体のGEEスクリプト
├── visualize_map.py                   # 汎用可視化スクリプト
└── README.md                          # 岩手県プロジェクトREADME
```

## 出力 / Output

### 1. コンソール出力 / Console Output

- 検出された水田の総面積 (ヘクタール、km²)
- 推定総農地面積
- 各期間の使用画像数
- 処理統計情報

### 2. エクスポート / Exports

Google Driveにエクスポート可能:
- 水田マスク画像 (GeoTIFF)
- 可視化画像 (PNG)

Can export to Google Drive:
- Paddy field mask (GeoTIFF)
- Visualization image (PNG)

### 3. 可視化マップ / Visualization Map

`visualize_morioka_2025.py` 実行後:
- インタラクティブHTML地図
- 各期間のNDVI/NDWI/SAR画像
- レイヤー切り替え機能

After running `visualize_morioka_2025.py`:
- Interactive HTML map
- NDVI/NDWI/SAR images for each period
- Layer toggle functionality

## 2025年干ばつの影響と対策 / 2025 Drought Impact and Countermeasures

### 干ばつの影響 / Drought Impact

7月の干ばつにより、通常の水田検出アルゴリズムでは以下の問題が発生:
- 水不足によりNDVIが通常より低下 (0.4〜0.5程度)
- 従来の閾値(NDVI > 0.6)では水田を見逃す可能性
- 水田と荒地の区別が困難

Due to the July drought, standard paddy field detection algorithms face issues:
- Water shortage causes lower NDVI values (around 0.4-0.5)
- Traditional threshold (NDVI > 0.6) may miss paddy fields
- Difficulty distinguishing paddy fields from fallow land

### 本システムの対策 / System Countermeasures

1. **動的閾値調整** / Dynamic Threshold Adjustment
   - 7月のNDVI閾値を0.3〜0.7に拡大
   - 期間ごとに最適な閾値を設定

2. **複数指標の併用** / Multiple Index Integration
   - NDVI、EVI、LSWI、NDWIを組み合わせ
   - EVIは干ばつ条件下で感度が高い

3. **SAR画像の重視** / Emphasis on SAR Imagery
   - 田植え期の湛水をSARで確実に検出
   - 光学画像の弱点を補完

4. **時系列パターン認識** / Time Series Pattern Recognition
   - 5期間の総合的な植生変化パターンで判定
   - 単一期間の異常値の影響を軽減

## 参考情報 / Reference Information

### 盛岡市・岩手県の農業統計 / Agricultural Statistics

- 岩手県水田面積: 約52,000ヘクタール (参考値)
- 農地に占める水田の割合: 約60%
- 主要作物: 米、りんご、野菜

- Iwate Prefecture paddy field area: Approximately 52,000 hectares (reference)
- Paddy fields as percentage of agricultural land: Approximately 60%
- Main crops: Rice, apples, vegetables

### 精度に影響する要因 / Factors Affecting Accuracy

1. **雲被覆** / Cloud Cover
   - クラウドカバー30%以下の画像を使用
   - 画像数が少ない場合は精度が低下する可能性

2. **地形** / Terrain
   - 山間部では影の影響を受ける可能性
   - 平野部で高精度

3. **作付け状況** / Cropping Patterns
   - 休耕田は検出されない
   - 遅い田植え/早い収穫は検出されない可能性

4. **干ばつの程度** / Drought Severity
   - 極端な干ばつの場合、さらなる調整が必要

## トラブルシューティング / Troubleshooting

### Q1: "No suitable images found" エラー

**原因**: 対象期間・地域で利用可能な衛星画像が不足

**対策**:
- クラウドカバー閾値を緩和 (30% → 50%)
- 期間を延長
- 2025年のデータが未だ利用できない場合、2024年で試す

### Q2: 面積が過大/過小評価される

**原因**: 閾値設定が地域特性に合っていない

**対策**:
- スクリプト内のNDVI/NDWI閾値を調整
- GEE Code Editorで各期間の画像を目視確認
- SAR画像の閾値も調整

### Q3: Google Earth Engine認証エラー

**原因**: GEEアカウント未登録または認証期限切れ

**対策**:
```bash
earthengine authenticate
```

## 今後の改善予定 / Future Improvements

- [ ] 機械学習モデルの導入 (Random Forest, CNN)
- [ ] 複数年のデータを使用した精度検証
- [ ] リアルタイム監視システムの構築
- [ ] 気象データとの統合
- [ ] 収量予測機能の追加

## ライセンス / License

MIT License

## 連絡先 / Contact

問題や改善提案がある場合は、GitHubのIssueで報告してください。

For issues or improvement suggestions, please report via GitHub Issues.

---

## 更新履歴 / Change Log

### 2025年版 (初版)
- 盛岡市中心半径50kmに特化
- 2025年7月干ばつ考慮アルゴリズム実装
- 5期間の詳細な時系列解析
- 農地60%が水田という統計情報を反映
- インタラクティブ可視化機能追加

### 2025 Version (First Release)
- Focused on 50km radius from Morioka City center
- Implemented drought-aware algorithm for July 2025
- Detailed 5-period time series analysis
- Incorporated 60% paddy field agricultural statistics
- Added interactive visualization features
