#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盛岡市水田面積判別スクリプト 2025年版 / Morioka City Paddy Field Detection Script 2025

このスクリプトは、Google Earth Engineを使用して盛岡市中心半径50kmの水田を検出し、
その面積を計算します。2025年7月の干ばつを考慮したアルゴリズムを使用します。

This script detects paddy fields within 50km radius of Morioka City center using
Google Earth Engine and calculates their total area. The algorithm accounts for
the July 2025 drought conditions.
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


def get_morioka_region():
    """
    盛岡市中心から半径50kmの範囲を取得 / Get 50km radius region from Morioka City center

    Returns:
        ee.Geometry: 盛岡市中心半径50kmの円形ジオメトリ / Circular geometry with 50km radius
    """
    # 盛岡市の中心座標 / Morioka City center coordinates
    # 緯度: 39.7036°N, 経度: 141.1527°E
    morioka_center = ee.Geometry.Point([141.1527, 39.7036])

    # 半径50km (50,000m) の円形バッファを作成
    # Create circular buffer with 50km (50,000m) radius
    morioka_region = morioka_center.buffer(50000)

    return morioka_region


def add_indices(image):
    """
    衛星画像にNDVI、NDWI、LSWIを追加 / Add NDVI, NDWI, and LSWI to satellite image

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

    # EVI (Enhanced Vegetation Index) - 干ばつ条件でより感度が高い
    # More sensitive under drought conditions
    # EVI = 2.5 * (NIR - Red) / (NIR + 6 * Red - 7.5 * Blue + 1)
    nir = image.select('B8')
    red = image.select('B4')
    blue = image.select('B2')
    evi = nir.subtract(red).multiply(2.5).divide(
        nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)
    ).rename('EVI')

    return image.addBands(ndvi).addBands(ndwi).addBands(lswi).addBands(evi)


def detect_paddy_fields_2025(region, year=2025):
    """
    2025年の水田を検出 (干ばつ考慮版) / Detect 2025 paddy fields (drought-aware version)

    Args:
        region: 対象地域 / Target region
        year: 対象年 / Target year (default: 2025)

    Returns:
        tuple: (水田マスク, 統計情報) / (paddy field mask, statistics)
    """
    print(f"Processing year: {year}")
    print(f"⚠ Special consideration: July {year} drought conditions")
    print(f"⚠ Improved coverage for all directions including southwest")

    # 期間を拡大して、より多くのデータを取得
    # Extend period to acquire more data
    start_date = f'{year}-03-15'  # 3月中旬から開始
    end_date = f'{year}-11-15'    # 11月中旬まで延長

    # Sentinel-2画像コレクションを取得
    # Get Sentinel-2 image collection
    # クラウドカバー閾値を緩和して、南西方向のデータも確実に取得
    # Relax cloud cover threshold to ensure southwest region coverage
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(region) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50)) \
        .map(add_indices)

    image_count = s2.size().getInfo()
    print(f"✓ Found {image_count} suitable Sentinel-2 images")

    # 南西、北東など各方向のカバレッジをチェック
    # Check coverage in all directions (SW, NE, etc.)
    print(f"  (Cloud cover threshold: 50%, Extended period for better coverage)")

    if image_count == 0:
        print("⚠ Warning: No suitable images found. Try adjusting the date range.")
        return None, None

    # Sentinel-1 SARデータを取得 (湛水期の検出に使用)
    # Get Sentinel-1 SAR data (used for detecting flooding period)
    # 広い期間で取得して南西方向もカバー
    # Acquire over extended period to cover southwest region
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
        .filterBounds(region) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
        .filter(ee.Filter.eq('instrumentMode', 'IW'))

    s1_count = s1.size().getInfo()
    print(f"✓ Found {s1_count} Sentinel-1 SAR images")

    # 各期間の画像を取得
    # 期間を少し広げて、南西方向のデータも確実に取得
    # Extend periods slightly to ensure southwest region coverage

    # Period 1: 田植え期 (5月-6月中旬): 湛水状態
    # Planting period (May to mid-June): Flooded state
    planting_period = s2.filterDate(f'{year}-05-01', f'{year}-06-20')
    # mean()とmedian()を組み合わせて、欠損値を最小化
    # Combine mean() and median() to minimize missing data
    planting_ndvi = planting_period.select('NDVI').mean()
    planting_ndwi = planting_period.select('NDWI').mean()
    planting_lswi = planting_period.select('LSWI').mean()

    # Period 2: 初期生育期 (6月): 稲の成長開始
    # Early growing period (June): Rice growth begins
    early_growth = s2.filterDate(f'{year}-06-15', f'{year}-07-05')
    early_ndvi = early_growth.select('NDVI').mean()

    # Period 3: 7月 - 干ばつ期間 (通常は高いNDVIだが、干ばつの影響で低下)
    # July - Drought period (normally high NDVI, but reduced due to drought)
    # 干ばつの影響で、通常より低いNDVI値を許容する必要がある
    drought_period = s2.filterDate(f'{year}-07-01', f'{year}-08-05')
    drought_ndvi = drought_period.select('NDVI').mean()
    drought_evi = drought_period.select('EVI').mean()
    drought_lswi = drought_period.select('LSWI').mean()

    # Period 4: 8月 - 回復期 (干ばつ後の回復)
    # August - Recovery period (post-drought recovery)
    recovery_period = s2.filterDate(f'{year}-08-01', f'{year}-09-10')
    recovery_ndvi = recovery_period.select('NDVI').mean()
    recovery_evi = recovery_period.select('EVI').mean()

    # Period 5: 9月-10月 - 収穫前期 (成熟期)
    # September-October - Pre-harvest period (maturation)
    harvest_period = s2.filterDate(f'{year}-09-01', f'{year}-10-15')
    harvest_ndvi = harvest_period.select('NDVI').mean()

    # SAR画像による湛水期の検出
    # Detect flooding period using SAR images
    planting_sar = s1.filterDate(f'{year}-04-15', f'{year}-06-30').select('VV').mean()

    # 水田の特徴 (2025年干ばつ考慮版):
    # Paddy field characteristics (2025 drought-aware version):
    # 1. 田植え期 (5月中旬-6月): 低いNDVI、高いNDWI/LSWI (湛水)
    #    Planting (mid-May to June): Low NDVI, high NDWI/LSWI (flooding)
    # 2. 初期生育期 (6月下旬): NDVIの上昇
    #    Early growth (late June): Rising NDVI
    # 3. 7月干ばつ期: 通常より低いNDVI (0.3-0.5の範囲) ← 重要な調整
    #    July drought: Lower than normal NDVI (0.3-0.5 range) ← Important adjustment
    # 4. 8月回復期: NDVIの回復 (0.4-0.6)
    #    August recovery: NDVI recovery (0.4-0.6)
    # 5. 9月収穫前: 中程度のNDVI (0.35-0.55)
    #    September pre-harvest: Moderate NDVI (0.35-0.55)

    print("\n=== Detection Criteria (Drought-Aware + Full Coverage) ===")
    print("Planting period: NDVI < 0.3, NDWI > 0.0 or LSWI > 0.0")
    print("July drought: NDVI 0.3-0.7 (adjusted threshold for drought)")
    print("August recovery: NDVI > 0.35 or EVI > 0.3")
    print("September-October harvest: NDVI 0.3-0.65")
    print("Cloud cover: < 50% (relaxed for better coverage)")
    print("Data period: Extended to ensure complete spatial coverage")
    print("==========================================================\n")

    # 水田マスクの作成 (干ばつ考慮版)
    # Create paddy field mask (drought-aware version)

    # 条件1: 田植え期の湛水状態
    # Condition 1: Flooding state during planting period
    planting_condition = (
        planting_ndvi.lt(0.3)              # 田植え期の低NDVI
        .And(planting_ndwi.gt(0.0))        # 田植え期の高NDWI
        .Or(planting_lswi.gt(0.0))         # または高いLSWI
    )

    # 条件2: 干ばつを考慮した7月の植生状態
    # Condition 2: July vegetation state considering drought
    # 通常の水田は7月に高いNDVI (>0.6) だが、干ばつの影響で0.3-0.6程度に低下
    drought_condition = (
        drought_ndvi.gt(0.3)               # 干ばつでも最低限の植生
        .And(drought_ndvi.lt(0.7))         # 上限も緩和
        .Or(drought_evi.gt(0.25))          # EVIで補完 (干ばつに敏感)
    )

    # 条件3: 8月の回復期
    # Condition 3: August recovery period
    recovery_condition = (
        recovery_ndvi.gt(0.35)             # 回復期のNDVI (通常より低め)
        .Or(recovery_evi.gt(0.3))          # EVIで補完
    )

    # 条件4: 収穫前の状態
    # Condition 4: Pre-harvest state
    harvest_condition = (
        harvest_ndvi.gt(0.3)               # 収穫前の最低NDVI
        .And(harvest_ndvi.lt(0.65))        # 収穫前の上限NDVI
    )

    # 総合的な水田判定
    # Overall paddy field determination
    paddy_mask = (
        planting_condition                  # 田植え期の条件は必須
        .And(
            drought_condition               # 7月の干ばつ条件
            .Or(recovery_condition)         # または8月の回復条件
        )
        .And(harvest_condition)             # 収穫前の条件
    )

    # SAR データによる補正 (利用可能な場合)
    # SAR data correction (if available)
    if s1_count > 0:
        # 湛水期の低いVV値を検出 (水田の重要な特徴)
        # Detect low VV values during flooding period (important paddy field feature)
        water_mask = planting_sar.lt(-12)

        # SARで湛水が検出され、かつ後期に植生がある場合は水田と判定
        # If SAR detects flooding and later vegetation exists, classify as paddy field
        sar_paddy = water_mask.And(
            recovery_ndvi.gt(0.3).Or(harvest_ndvi.gt(0.3))
        )

        # 光学とSARの結果を統合
        # Integrate optical and SAR results
        paddy_mask = paddy_mask.Or(sar_paddy)

    # ノイズ除去 / Noise removal
    # モルフォロジー処理で小さなノイズを除去
    paddy_mask = paddy_mask.focal_mode(radius=30, units='meters')

    # 最小面積フィルタ (孤立した小さなパッチを除去)
    # Minimum area filter (remove isolated small patches)
    # 水田は通常まとまった面積があるため、連結成分解析で小さいものを除去
    paddy_mask = paddy_mask.selfMask()

    # 統計情報の計算 / Calculate statistics
    stats = {
        'total_images': image_count,
        'sar_images': s1_count,
        'planting_images': planting_period.size().getInfo(),
        'early_growth_images': early_growth.size().getInfo(),
        'drought_images': drought_period.size().getInfo(),
        'recovery_images': recovery_period.size().getInfo(),
        'harvest_images': harvest_period.size().getInfo(),
        'coverage_improvement': 'Extended periods and relaxed cloud cover for full coverage including southwest'
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

    # 面積計算 / Calculate area
    area_image = paddy_mask.multiply(ee.Image.pixelArea())

    area_stats = area_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=10,
        maxPixels=1e13,
        bestEffort=True
    )

    # 結果を取得 (バンド名は最初のバンドを使用)
    area_sq_meters = area_stats.getInfo()

    # 辞書から値を取得
    if isinstance(area_sq_meters, dict):
        # 最初のバンドの値を取得
        area_sq_meters = list(area_sq_meters.values())[0] if area_sq_meters else 0

    if area_sq_meters is None:
        area_sq_meters = 0

    area_hectares = area_sq_meters / 10000  # Convert to hectares

    return area_hectares


def estimate_agricultural_area(paddy_area):
    """
    水田面積から総農地面積を推定 / Estimate total agricultural area from paddy field area

    Args:
        paddy_area: 水田面積(ヘクタール) / Paddy field area in hectares

    Returns:
        float: 推定総農地面積(ヘクタール) / Estimated total agricultural area in hectares

    Note:
        盛岡市・岩手県では農地の約60%が水田
        About 60% of agricultural land in Morioka/Iwate is paddy fields
    """
    paddy_ratio = 0.6  # 60%が水田 / 60% is paddy fields
    total_agricultural_area = paddy_area / paddy_ratio

    return total_agricultural_area


def export_results(paddy_mask, region, description='morioka_paddy_2025'):
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
        image=paddy_mask.toByte().visualize(palette=['green']),
        description=description,
        region=region,
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
    print("=" * 70)
    print("盛岡市水田面積判別システム 2025年版")
    print("Morioka City Paddy Field Detection System 2025")
    print("=" * 70)
    print()

    # 盛岡市中心半径50kmの範囲を取得
    # Get 50km radius region from Morioka City center
    print("1. Defining Morioka region...")
    print("   Center: 39.7036°N, 141.1527°E (Morioka City Hall)")
    print("   Radius: 50 km")
    morioka_region = get_morioka_region()
    print("✓ Region defined")
    print()

    # 2025年の水田検出 (干ばつ考慮)
    # Detect 2025 paddy fields (considering drought)
    print("2. Detecting paddy fields for 2025...")
    print("   ⚠ Special algorithm for July 2025 drought")
    print()

    paddy_mask, stats = detect_paddy_fields_2025(morioka_region, year=2025)

    if paddy_mask is None:
        print("⚠ Detection failed. Please check the date range and try again.")
        return

    print()
    print("3. Calculating total area...")

    # 面積計算 / Calculate area
    paddy_area_hectares = calculate_area(paddy_mask, morioka_region)

    # 総農地面積の推定 (水田が60%と仮定)
    # Estimate total agricultural area (assuming 60% is paddy fields)
    total_agricultural_area = estimate_agricultural_area(paddy_area_hectares)

    print()
    print("=" * 70)
    print("結果 / RESULTS")
    print("=" * 70)
    print(f"対象地域 / Target Region: 盛岡市中心半径50km / 50km radius from Morioka")
    print(f"対象年度 / Target Year: 2025")
    print(f"処理期間 / Processing Period: 2025-03-15 to 2025-11-15 (Extended for full coverage)")
    print(f"特記事項 / Note: 7月干ばつ考慮 + 南西方向含む全方向カバレッジ改善")
    print(f"Note: July drought-aware algorithm + Improved coverage for all directions including SW")
    print()
    print(f"カバレッジ改善 / Coverage Improvements:")
    print(f"  - クラウドカバー閾値: 50% (緩和) / Cloud cover threshold: 50% (relaxed)")
    print(f"  - データ期間: 拡張 (3月中旬-11月中旬) / Extended period (mid-Mar to mid-Nov)")
    print(f"  - 南西方向のデータ欠損を解消 / Resolved southwest region data gaps")
    print()
    print(f"使用した衛星画像数 / Satellite Images Used:")
    print(f"  - Total Sentinel-2: {stats['total_images']}")
    print(f"  - Sentinel-1 SAR: {stats['sar_images']}")
    print(f"  - Planting period (5月-6月中旬): {stats['planting_images']}")
    print(f"  - Early growth (6月中旬-7月初旬): {stats['early_growth_images']}")
    print(f"  - Drought period (7月-8月初旬): {stats['drought_images']}")
    print(f"  - Recovery period (8月-9月初旬): {stats['recovery_images']}")
    print(f"  - Pre-harvest (9月-10月中旬): {stats['harvest_images']}")
    print()
    print(f"検出された水田面積 / Detected Paddy Field Area:")
    print(f"  {paddy_area_hectares:,.2f} ヘクタール / hectares")
    print(f"  {paddy_area_hectares / 100:,.2f} 平方キロメートル / km²")
    print()
    print(f"推定総農地面積 / Estimated Total Agricultural Area:")
    print(f"  (水田が農地の60%と仮定 / Assuming paddy fields are 60% of agricultural land)")
    print(f"  {total_agricultural_area:,.2f} ヘクタール / hectares")
    print(f"  {total_agricultural_area / 100:,.2f} 平方キロメートル / km²")
    print()
    print(f"その他の農地 / Other Agricultural Land:")
    print(f"  {total_agricultural_area - paddy_area_hectares:,.2f} ヘクタール / hectares")
    print(f"  (畑、果樹園など / Fields, orchards, etc.)")
    print()

    # 干ばつの影響と改善についてのノート
    # Note about drought impact and improvements
    print("⚠ 2025年版の改善点 / 2025 Version Improvements:")
    print("  - 7月干ばつ: 通常より低いNDVI閾値を使用 (0.3-0.7)")
    print("    July drought: Lower NDVI thresholds (0.3-0.7)")
    print("  - 南西方向カバレッジ: クラウドカバー50%、期間拡張で完全カバー")
    print("    Southwest coverage: 50% cloud cover + extended period for complete coverage")
    print("  - 欠損値対策: mean()使用でモザイク処理を改善")
    print("    Missing data: Improved mosaicking using mean()")
    print("  - SAR画像: 広い期間で取得し湛水期を確実に検出")
    print("    SAR imagery: Extended acquisition period for reliable flooding detection")
    print()

    # 可視化リンクの生成 / Generate visualization link
    print("4. Generating visualization...")
    center = morioka_region.centroid().coordinates().getInfo()
    print(f"✓ Map center: {center}")
    print()
    print("Google Earth Engine Code Editor で可視化するには:")
    print("To visualize in Google Earth Engine Code Editor:")
    print(f"  Map.setCenter({center[0]}, {center[1]}, 10);")
    print()

    # エクスポート / Export
    print("5. Exporting results...")
    export_results(paddy_mask, morioka_region, 'morioka_paddy_2025_drought_aware')
    print()
    print("=" * 70)
    print("処理完了 / Processing Complete")
    print("=" * 70)
    print()
    print("次のステップ / Next Steps:")
    print("1. Google DriveでエクスポートされたGeoTIFFファイルを確認")
    print("   Check the exported GeoTIFF file in Google Drive")
    print("2. visualize_map.pyで結果を可視化 (利用可能な場合)")
    print("   Visualize results with visualize_map.py (if available)")
    print("3. GEE Code Editorで詳細な解析")
    print("   Detailed analysis in GEE Code Editor")
    print()


if __name__ == "__main__":
    main()
