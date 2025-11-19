# 岩手県水田面積判別 / Iwate Paddy Field Detection

Google Earth Engineを使用して岩手県の水田面積を検出・推定するプロジェクトです。

A project to detect and estimate paddy field areas in Iwate Prefecture, Japan using Google Earth Engine.

## 概要 / Overview

このプロジェクトは、衛星画像データとGoogle Earth Engine (GEE) APIを使用して、岩手県内の水田を自動的に識別し、その面積を計算します。

This project uses satellite imagery data and the Google Earth Engine (GEE) API to automatically identify rice paddy fields in Iwate Prefecture and calculate their total area.

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

### 水田検出 / Paddy Field Detection

```bash
# GEEの認証
earthengine authenticate

# スクリプト実行
python iwate_paddy_detection.py
```

### GeoJSONファイルのマージ / Merging GeoJSON Files

複数のGeoJSONファイルを一つのFeatureCollectionにまとめる場合:

```bash
# 基本的な使用方法
python merge_geojson.py <入力ディレクトリ> [出力ファイル名]

# 例: fude2025_03ディレクトリ内の全GeoJSONをマージ
python merge_geojson.py ./fude2025_03

# 出力ファイル名を指定
python merge_geojson.py ./fude2025_03 merged_output.geojson
```

このツールは:
- 指定ディレクトリ内の全ての.geojsonおよび.jsonファイルを検索
- FeatureCollectionおよび単一Featureの両方に対応
- マージ結果をArcGIS互換のGeoJSON形式で出力
- 処理の進捗と統計情報を表示

## ファイル構成 / File Structure

- `iwate_paddy_detection.py`: メインスクリプト / Main detection script
- `merge_geojson.py`: GeoJSONファイルマージツール / GeoJSON merge tool
- `requirements.txt`: 必要なPythonパッケージ / Required Python packages
- `README.md`: このファイル / This file

## 出力 / Output

スクリプトは以下を出力します:
- 検出された水田の総面積 (ヘクタール)
- GEE上での可視化用のマップリンク
- 処理結果の統計情報

The script outputs:
- Total area of detected paddy fields (hectares)
- Map link for visualization on GEE
- Statistical information of processing results

## 注意事項 / Notes

- Google Earth Engineの使用にはアカウント登録が必要です
- 処理には数分かかる場合があります
- クラウドカバーが多い画像は自動的にフィルタリングされます

- Google Earth Engine account registration is required
- Processing may take several minutes
- Images with high cloud cover are automatically filtered

## ライセンス / License

MIT License
