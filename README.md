# 岩手県水田面積判別 / Iwate Paddy Field Detection

Google Earth Engineを使用して岩手県の水田面積を検出・推定するプロジェクトです（複数年対応版）。

A project to detect and estimate paddy field areas in Iwate Prefecture, Japan using Google Earth Engine (Multi-Year Support).

## 概要 / Overview

このプロジェクトは、衛星画像データとGoogle Earth Engine (GEE) APIを使用して、岩手県内の水田を自動的に識別し、その面積を計算します。2018年から2025年までの複数年次のデータを処理し、年次別の水田面積変化を追跡できます。

This project uses satellite imagery data and the Google Earth Engine (GEE) API to automatically identify rice paddy fields in Iwate Prefecture and calculate their total area. It processes multi-year data from 2018 to 2025, enabling tracking of annual changes in paddy field areas.

## 新機能 / New Features

- **複数年次対応**: 2018年から2025年までの8年間のデータを処理
- **年次別面積計算**: 各年の水田面積を自動計算
- **視覚的な凡例**: 年次別の色分けされた凡例を地図上に表示
- **一括エクスポート**: 全年次のGeoTIFFデータを一括でエクスポート可能

- **Multi-Year Support**: Process data from 2018 to 2025 (8 years)
- **Annual Area Calculation**: Automatically calculate paddy field areas for each year
- **Visual Legend**: Display color-coded legend for each year on the map
- **Batch Export**: Export GeoTIFF data for all years at once

## 手法 / Methodology

1. **衛星データ**: Sentinel-2およびSentinel-1データを使用
2. **植生指数**: NDVI (Normalized Difference Vegetation Index) を計算
3. **水分指数**: NDWI (Normalized Difference Water Index) を計算
4. **SAR データ**: 水田の湛水期を検出するためにSentinel-1のVVおよびVH偏波を使用
5. **時系列解析**: 水田特有の季節変動パターンを検出

1. **Satellite Data**: Uses Sentinel-2 and Sentinel-1 data
2. **Vegetation Index**: Calculates NDVI (Normalized Difference Vegetation Index)
3. **Water Index**: Calculates NDWI (Normalized Difference Water Index)
4. **SAR Data**: Uses Sentinel-1 VV and VH polarization to detect flooding period
5. **Time Series Analysis**: Detects seasonal variation patterns unique to paddy fields

## 必要な環境 / Requirements

- Python 3.7+
- Google Earth Engine account
- earthengine-api
- geopandas (オプション / optional)

## インストール / Installation

```bash
pip install -r requirements.txt
```

## 使用方法 / Usage

### Google Earth Engine Code Editorで使用する場合 / Using with GEE Code Editor

1. [Google Earth Engine Code Editor](https://code.earthengine.google.com/)にアクセス
2. `iwate_paddy_detection.js`の内容をコピー&ペースト
3. Runボタンをクリックして実行
4. Tasksタブから各年次のGeoTIFFをエクスポート

1. Access [Google Earth Engine Code Editor](https://code.earthengine.google.com/)
2. Copy and paste the contents of `iwate_paddy_detection.js`
3. Click the Run button to execute
4. Export GeoTIFF files for each year from the Tasks tab

### Pythonで使用する場合 / Using with Python

```bash
# GEEの認証
earthengine authenticate

# スクリプト実行
python iwate_paddy_detection.py
```

## ファイル構成 / File Structure

- `iwate_paddy_detection.js`: Google Earth Engine Code Editor用スクリプト（複数年対応） / GEE Code Editor script (Multi-Year Support)
- `iwate_paddy_detection.py`: Pythonメインスクリプト / Python main detection script
- `visualize_map.py`: 地図可視化用スクリプト / Map visualization script
- `requirements.txt`: 必要なPythonパッケージ / Required Python packages
- `README.md`: このファイル / This file

## 出力 / Output

スクリプトは以下を出力します:
- **年次別水田面積**: 2018年から2025年までの各年の水田面積（ヘクタール）
- **インタラクティブマップ**: 各年次の水田を色分けして表示
- **凡例**: 年次別の色分け凡例
- **GeoTIFFエクスポート**: 各年次のラスターデータ（iwate_paddy_2018.tif ~ iwate_paddy_2025.tif）

The script outputs:
- **Annual Paddy Areas**: Paddy field areas for each year from 2018 to 2025 (hectares)
- **Interactive Map**: Color-coded display of paddy fields for each year
- **Legend**: Color-coded legend for each year
- **GeoTIFF Export**: Raster data for each year (iwate_paddy_2018.tif ~ iwate_paddy_2025.tif)

## 可視化の色分け / Color Coding

各年次は以下の色で表示されます:

- 2018年: ダークレッド / Dark Red (#8B0000)
- 2019年: オレンジレッド / Orange Red (#FF4500)
- 2020年: オレンジ / Orange (#FFA500)
- 2021年: ゴールド / Gold (#FFD700)
- 2022年: グリーンイエロー / Green Yellow (#ADFF2F)
- 2023年: ミディアムスプリンググリーン / Medium Spring Green (#00FA9A)
- 2024年: ダークターコイズ / Dark Turquoise (#00CED1)
- 2025年: ドジャーブルー / Dodger Blue (#1E90FF)

## 注意事項 / Notes

- Google Earth Engineの使用にはアカウント登録が必要です
- 処理には数分かかる場合があります
- クラウドカバーが多い画像は自動的にフィルタリングされます

- Google Earth Engine account registration is required
- Processing may take several minutes
- Images with high cloud cover are automatically filtered

## ライセンス / License

MIT License
