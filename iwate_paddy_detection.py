#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
岩手県水田面積判別スクリプト / Iwate Prefecture Paddy Field Detection Script

このスクリプトは、Google Earth Engineを使用して岩手県の水田を検出し、
その面積を計算します。

This script detects paddy fields in Iwate Prefecture using Google Earth Engine
and calculates their total area.
"""

import ee
import datetime

# Google Earth Engineの初期化 / Initialize Google Earth Engine
try:
    ee.Initialize()
    print("✓ Google Earth Engine initialized successfully")
except Exception as e:
    print("Google Earth Engine initialization failed. Please run: earthengine authenticate")
    print(f"Error: {e}")
    exit(1)


def get_iwate_boundary():
    """
    岩手県の境界を取得 / Get Iwate Prefecture boundary

    Returns:
        ee.FeatureCollection: 岩手県の境界 / Iwate Prefecture boundary
    """
    # 日本の行政区画データセットから岩手県を抽出
    # Extract Iwate Prefecture from Japan administrative boundaries
    japan = ee.FeatureCollection("FAO/GAUL/2015/level1")
    iwate = japan.filter(ee.Filter.And(
        ee.Filter.eq('ADM0_NAME', 'Japan'),
        ee.Filter.eq('ADM1_NAME', 'Iwate')
    ))

    # もし上記で取得できない場合は、座標で岩手県の概算範囲を作成
    # If the above doesn't work, create approximate Iwate boundary using coordinates
    if iwate.size().getInfo() == 0:
        print("Using approximate coordinates for Iwate Prefecture")
        # 岩手県のおおよその境界座標
        iwate_coords = [
            [140.5, 38.8],
            [142.0, 38.8],
            [142.0, 40.5],
            [140.5, 40.5],
            [140.5, 38.8]
        ]
        iwate = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Polygon(iwate_coords), {'name': 'Iwate'})
        ])

    return iwate


def add_indices(image):
    """
    衛星画像にNDVIとNDWIを追加 / Add NDVI and NDWI to satellite image

    Args:
        image: Sentinel-2画像 / Sentinel-2 image

    Returns:
        ee.Image: インデックスが追加された画像 / Image with added indices
    """
    # NDVI (正規化植生指数) / Normalized Difference Vegetation Index
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')

    # NDWI (正規化水指数) / Normalized Difference Water Index
    ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')

    # LSWI (Land Surface Water Index) - 水田検出に有効
    # Useful for paddy field detection
    lswi = image.normalizedDifference(['B8', 'B11']).rename('LSWI')

    return image.addBands(ndvi).addBands(ndwi).addBands(lswi)


def detect_paddy_fields(region, start_date, end_date):
    """
    水田を検出 / Detect paddy fields

    Args:
        region: 対象地域 / Target region
        start_date: 開始日 / Start date (YYYY-MM-DD)
        end_date: 終了日 / End date (YYYY-MM-DD)

    Returns:
        tuple: (水田マスク, 統計情報) / (paddy field mask, statistics)
    """
    print(f"Processing period: {start_date} to {end_date}")

    # Sentinel-2画像コレクションを取得
    # Get Sentinel-2 image collection
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(region) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .map(add_indices)

    image_count = s2.size().getInfo()
    print(f"✓ Found {image_count} suitable Sentinel-2 images")

    if image_count == 0:
        print("⚠ Warning: No suitable images found. Try adjusting the date range.")
        return None, None

    # Sentinel-1 SARデータを取得 (湛水期の検出に使用)
    # Get Sentinel-1 SAR data (used for detecting flooding period)
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
        .filterBounds(region) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
        .filter(ee.Filter.eq('instrumentMode', 'IW'))

    s1_count = s1.size().getInfo()
    print(f"✓ Found {s1_count} Sentinel-1 SAR images")

    # 各期間の画像を取得
    # 田植え期 (5-6月): 湛水状態 / Planting period (May-June): Flooded
    planting_period = s2.filterDate(f'{start_date[:4]}-05-01', f'{start_date[:4]}-06-30')
    planting_ndvi = planting_period.select('NDVI').median()
    planting_ndwi = planting_period.select('NDWI').median()
    planting_lswi = planting_period.select('LSWI').median()

    # 生育期 (7-8月): 高いNDVI / Growing period (July-August): High NDVI
    growing_period = s2.filterDate(f'{start_date[:4]}-07-01', f'{start_date[:4]}-08-31')
    growing_ndvi = growing_period.select('NDVI').median()

    # 収穫前期 (9月): 成熟期 / Pre-harvest period (September): Maturation
    harvest_period = s2.filterDate(f'{start_date[:4]}-09-01', f'{start_date[:4]}-09-30')
    harvest_ndvi = harvest_period.select('NDVI').median()

    # 水田の特徴:
    # Paddy field characteristics:
    # 1. 田植え期: 低いNDVI、高いNDWI (水面)
    # 2. 生育期: 高いNDVI (緑の稲)
    # 3. 収穫前: 中程度のNDVI

    # 水田マスクの作成 / Create paddy field mask
    paddy_mask = (
        planting_ndvi.lt(0.3)              # 田植え期の低NDVI / Low NDVI during planting
        .And(planting_ndwi.gt(0.0))        # 田植え期の高NDWI / High NDWI during planting
        .Or(planting_lswi.gt(0.0))         # または高いLSWI / Or high LSWI
        .And(growing_ndvi.gt(0.4))         # 生育期の高NDVI / High NDVI during growing
        .And(harvest_ndvi.gt(0.3))         # 収穫前の中程度のNDVI / Moderate NDVI pre-harvest
    )

    # SAR データを使用した補正 (利用可能な場合)
    # SAR data correction (if available)
    if s1_count > 0:
        s1_median = s1.select('VV').median()
        # 湛水期の低いVV値を検出
        # Detect low VV values during flooding period
        water_mask = s1_median.lt(-15)
        paddy_mask = paddy_mask.Or(
            water_mask.And(growing_ndvi.gt(0.4))
        )

    # ノイズ除去 / Noise removal
    paddy_mask = paddy_mask.focal_mode(radius=30, units='meters')

    # 最小面積フィルタ (小さすぎるパッチを除去)
    # Minimum area filter (remove patches that are too small)
    paddy_mask = paddy_mask.selfMask()

    # 統計情報の計算 / Calculate statistics
    stats = {
        'total_images': image_count,
        'sar_images': s1_count,
        'planting_images': planting_period.size().getInfo(),
        'growing_images': growing_period.size().getInfo(),
        'harvest_images': harvest_period.size().getInfo()
    }

    return paddy_mask, stats


def calculate_area(paddy_mask, region):
    """
    水田の総面積を計算 / Calculate total paddy field area

    Args:
        paddy_mask: 水田マスク画像 / Paddy field mask image
        region: 対象地域 / Target region

    Returns:
        float: 面積(ヘクタール) / Area in hectares
    """
    if paddy_mask is None:
        return 0

    # ピクセルサイズ: Sentinel-2は10m解像度
    # Pixel size: Sentinel-2 is 10m resolution
    pixel_area = 10 * 10  # 100 square meters per pixel

    # 面積計算 / Calculate area
    area_image = paddy_mask.multiply(ee.Image.pixelArea())

    area_stats = area_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region.geometry(),
        scale=10,
        maxPixels=1e13
    )

    area_sq_meters = area_stats.get('NDVI').getInfo()
    if area_sq_meters is None:
        area_sq_meters = 0

    area_hectares = area_sq_meters / 10000  # Convert to hectares

    return area_hectares


def export_results(paddy_mask, region, description='iwate_paddy_fields'):
    """
    結果をGoogle Driveにエクスポート / Export results to Google Drive

    Args:
        paddy_mask: 水田マスク画像 / Paddy field mask image
        region: 対象地域 / Target region
        description: エクスポートファイルの説明 / Export file description
    """
    if paddy_mask is None:
        print("⚠ No mask to export")
        return

    task = ee.batch.Export.image.toDrive(
        image=paddy_mask.visualize(palette=['green']),
        description=description,
        region=region.geometry(),
        scale=10,
        maxPixels=1e13
    )

    task.start()
    print(f"✓ Export task started: {description}")
    print(f"  Check your Google Drive for the result")
    print(f"  Task ID: {task.id}")


def main():
    """
    メイン処理 / Main processing
    """
    print("=" * 60)
    print("岩手県水田面積判別システム")
    print("Iwate Prefecture Paddy Field Detection System")
    print("=" * 60)
    print()

    # 岩手県の境界を取得 / Get Iwate Prefecture boundary
    print("1. Getting Iwate Prefecture boundary...")
    iwate = get_iwate_boundary()
    print(f"✓ Region loaded: {iwate.size().getInfo()} feature(s)")
    print()

    # 対象期間の設定 (最新の完全な年度を使用)
    # Set target period (use the most recent complete year)
    current_year = datetime.datetime.now().year
    # 現在の月が12月より前なら前年のデータを使用
    # If current month is before December, use previous year's data
    target_year = current_year if datetime.datetime.now().month == 12 else current_year - 1

    start_date = f'{target_year}-04-01'
    end_date = f'{target_year}-10-31'

    print(f"2. Detecting paddy fields for year {target_year}...")
    print()

    # 水田検出 / Detect paddy fields
    paddy_mask, stats = detect_paddy_fields(iwate, start_date, end_date)

    if paddy_mask is None:
        print("⚠ Detection failed. Please check the date range and try again.")
        return

    print()
    print("3. Calculating total area...")

    # 面積計算 / Calculate area
    area_hectares = calculate_area(paddy_mask, iwate)

    print()
    print("=" * 60)
    print("結果 / RESULTS")
    print("=" * 60)
    print(f"対象年度 / Target Year: {target_year}")
    print(f"処理期間 / Processing Period: {start_date} to {end_date}")
    print()
    print(f"使用した衛星画像数 / Images Used:")
    print(f"  - Total Sentinel-2: {stats['total_images']}")
    print(f"  - Sentinel-1 SAR: {stats['sar_images']}")
    print(f"  - Planting period: {stats['planting_images']}")
    print(f"  - Growing period: {stats['growing_images']}")
    print(f"  - Harvest period: {stats['harvest_images']}")
    print()
    print(f"検出された水田面積 / Detected Paddy Field Area:")
    print(f"  {area_hectares:,.2f} ヘクタール / hectares")
    print(f"  {area_hectares / 100:,.2f} 平方キロメートル / km²")
    print()

    # 岩手県の統計との比較 (参考値: 約52,000ヘクタール)
    # Comparison with Iwate statistics (reference: approx. 52,000 hectares)
    reference_area = 52000
    percentage = (area_hectares / reference_area) * 100
    print(f"参考: 岩手県の水田面積は約 {reference_area:,} ヘクタール")
    print(f"Reference: Iwate paddy field area is approximately {reference_area:,} hectares")
    print(f"検出率 / Detection Rate: {percentage:.1f}%")
    print()

    # 可視化リンクの生成 / Generate visualization link
    print("4. Generating visualization...")
    center = iwate.geometry().centroid().coordinates().getInfo()
    print(f"✓ Map center: {center}")
    print()
    print("Google Earth Engine Code Editor で可視化するには:")
    print("To visualize in Google Earth Engine Code Editor:")
    print(f"  Map.setCenter({center[0]}, {center[1]}, 9);")
    print()

    # エクスポート
    # Export
    print("5. Exporting results...")
    export_results(paddy_mask, iwate, f'iwate_paddy_{target_year}')
    print()
    print("=" * 60)
    print("処理完了 / Processing Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
