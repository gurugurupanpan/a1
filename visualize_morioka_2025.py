#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盛岡市水田検出結果可視化スクリプト 2025年版
Morioka City Paddy Field Detection Result Visualization Script 2025

このスクリプトは、Google Earth Engineで検出した水田結果を
詳細に可視化・分析します。

This script provides detailed visualization and analysis of paddy field
detection results from Google Earth Engine.
"""

import ee
import folium
from datetime import datetime

# Google Earth Engineの初期化 / Initialize Google Earth Engine
try:
    ee.Initialize()
    print("✓ Google Earth Engine initialized successfully")
except Exception as e:
    print("Google Earth Engine initialization failed.")
    print("Please run: earthengine authenticate")
    print(f"Error: {e}")
    exit(1)


def get_morioka_region():
    """
    盛岡市中心から半径50kmの範囲を取得 / Get 50km radius region from Morioka City center
    """
    morioka_center = ee.Geometry.Point([141.1527, 39.7036])
    morioka_region = morioka_center.buffer(50000)
    return morioka_region, morioka_center


def add_ee_layer(self, ee_image_object, vis_params, name):
    """
    Foliumマップに Earth Engine レイヤーを追加する補助関数
    Helper function to add Earth Engine layers to folium map
    """
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        name=name,
        overlay=True,
        control=True
    ).add_to(self)


# foliumのMapクラスにメソッドを追加
# Add method to folium Map class
folium.Map.add_ee_layer = add_ee_layer


def create_visualization_map(year=2025):
    """
    インタラクティブな可視化マップを作成
    Create interactive visualization map

    Args:
        year: 対象年 / Target year

    Returns:
        folium.Map: インタラクティブマップ / Interactive map
    """
    print(f"Creating visualization map for {year}...")

    # 盛岡市の範囲を取得 / Get Morioka region
    morioka_region, morioka_center = get_morioka_region()
    center_coords = morioka_center.coordinates().getInfo()

    # Foliumマップを作成 / Create folium map
    # 中心: 盛岡市 / Center: Morioka City
    m = folium.Map(
        location=[39.7036, 141.1527],
        zoom_start=10,
        tiles='OpenStreetMap'
    )

    # ベースマップの追加 / Add base maps
    folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)

    # 盛岡市中心マーカー / Morioka center marker
    folium.Marker(
        [39.7036, 141.1527],
        popup='盛岡市役所<br>Morioka City Hall',
        tooltip='盛岡市中心 / Morioka Center',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)

    # 範囲円の追加 / Add range circle
    folium.Circle(
        location=[39.7036, 141.1527],
        radius=50000,  # 50km
        color='blue',
        fill=True,
        fillColor='blue',
        fillOpacity=0.1,
        popup='対象範囲: 半径50km<br>Target Range: 50km radius',
        tooltip='対象範囲 / Target Range'
    ).add_to(m)

    print("✓ Base map created")

    # Sentinel-2画像とインデックスを取得 / Get Sentinel-2 images and indices
    try:
        # 画像取得の準備 / Prepare to get images
        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(morioka_region) \
            .filterDate(f'{year}-04-01', f'{year}-10-31') \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))

        # 各期間の画像
        # 回復期 (8月) の画像を代表として使用
        # Use recovery period (August) image as representative
        recovery_period = s2.filterDate(f'{year}-08-01', f'{year}-08-31')

        if recovery_period.size().getInfo() > 0:
            rgb_image = recovery_period.median().clip(morioka_region)

            # RGB可視化 / RGB visualization
            rgb_vis = {
                'min': 0,
                'max': 3000,
                'bands': ['B4', 'B3', 'B2']
            }
            m.add_ee_layer(rgb_image, rgb_vis, 'Sentinel-2 RGB (8月 / August)')

            # NDVI可視化 / NDVI visualization
            ndvi = rgb_image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            ndvi_vis = {
                'min': -0.2,
                'max': 0.8,
                'palette': ['blue', 'white', 'green']
            }
            m.add_ee_layer(ndvi, ndvi_vis, 'NDVI (8月 / August)')

            print("✓ Sentinel-2 layers added")

    except Exception as e:
        print(f"⚠ Warning: Could not add Sentinel-2 layers: {e}")

    # 凡例の追加 / Add legend
    legend_html = '''
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 250px; height: auto;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <h4 style="margin-top:0">凡例 / Legend</h4>
    <p><strong>盛岡市水田検出 2025</strong></p>
    <p><i class="fa fa-circle" style="color:red"></i> 盛岡市中心<br>Morioka Center</p>
    <p><i class="fa fa-circle" style="color:blue"></i> 対象範囲 (50km)<br>Target Range</p>
    <p><strong>NDVI:</strong><br>
    <span style="color:blue">■</span> 水域 / Water<br>
    <span style="color:white">■</span> 裸地 / Bare Soil<br>
    <span style="color:green">■</span> 植生 / Vegetation</p>
    <p style="font-size:11px; color:gray">
    ⚠ 2025年7月干ばつ考慮<br>
    Drought-aware algorithm
    </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # レイヤーコントロールを追加 / Add layer control
    folium.LayerControl().add_to(m)

    print("✓ Visualization map created successfully")

    return m


def generate_statistics_report(year=2025):
    """
    統計レポートを生成 / Generate statistics report

    Args:
        year: 対象年 / Target year

    Returns:
        dict: 統計情報 / Statistics
    """
    print(f"\nGenerating statistics report for {year}...")

    morioka_region, _ = get_morioka_region()

    # Sentinel-2データの統計
    # Sentinel-2 data statistics
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(morioka_region) \
        .filterDate(f'{year}-04-01', f'{year}-10-31') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))

    total_images = s2.size().getInfo()

    # 各期間の画像数
    # Image counts for each period
    periods = {
        'planting': (f'{year}-05-15', f'{year}-06-20'),
        'early_growth': (f'{year}-06-21', f'{year}-06-30'),
        'drought': (f'{year}-07-01', f'{year}-07-31'),
        'recovery': (f'{year}-08-01', f'{year}-08-31'),
        'harvest': (f'{year}-09-01', f'{year}-09-30')
    }

    period_counts = {}
    for period_name, (start, end) in periods.items():
        count = s2.filterDate(start, end).size().getInfo()
        period_counts[period_name] = count

    # Sentinel-1データの統計
    # Sentinel-1 data statistics
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
        .filterBounds(morioka_region) \
        .filterDate(f'{year}-05-01', f'{year}-06-20') \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))

    sar_images = s1.size().getInfo()

    stats = {
        'year': year,
        'total_images': total_images,
        'sar_images': sar_images,
        'period_counts': period_counts,
        'processing_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # レポート出力 / Print report
    print("\n" + "=" * 60)
    print(f"統計レポート / Statistics Report - {year}")
    print("=" * 60)
    print(f"処理日時 / Processing Date: {stats['processing_date']}")
    print(f"対象範囲 / Target Region: 盛岡市中心半径50km")
    print()
    print(f"利用可能な画像数 / Available Images:")
    print(f"  - Sentinel-2 Total: {total_images}")
    print(f"  - Sentinel-1 SAR: {sar_images}")
    print()
    print(f"期間別画像数 / Images per Period:")
    print(f"  - 田植え期 (5月中旬-6月中旬) / Planting: {period_counts['planting']}")
    print(f"  - 初期生育期 (6月下旬) / Early Growth: {period_counts['early_growth']}")
    print(f"  - 干ばつ期 (7月) / Drought: {period_counts['drought']}")
    print(f"  - 回復期 (8月) / Recovery: {period_counts['recovery']}")
    print(f"  - 収穫前期 (9月) / Pre-harvest: {period_counts['harvest']}")
    print("=" * 60)

    return stats


def save_map(map_obj, filename='morioka_paddy_map_2025.html'):
    """
    マップをHTMLファイルとして保存
    Save map as HTML file

    Args:
        map_obj: Foliumマップオブジェクト / Folium map object
        filename: 保存するファイル名 / Filename to save
    """
    try:
        map_obj.save(filename)
        print(f"\n✓ Map saved as: {filename}")
        print(f"  Open this file in a web browser to view the interactive map")
    except Exception as e:
        print(f"⚠ Error saving map: {e}")


def main():
    """
    メイン処理 / Main processing
    """
    print("=" * 70)
    print("盛岡市水田検出結果可視化システム 2025")
    print("Morioka City Paddy Field Detection Visualization System 2025")
    print("=" * 70)
    print()

    # 統計レポート生成 / Generate statistics report
    stats = generate_statistics_report(year=2025)

    # 可視化マップ作成 / Create visualization map
    print("\n" + "=" * 70)
    print("可視化マップ作成中 / Creating Visualization Map")
    print("=" * 70)

    viz_map = create_visualization_map(year=2025)

    # マップを保存 / Save map
    save_map(viz_map, 'morioka_paddy_map_2025.html')

    print()
    print("=" * 70)
    print("完了 / Complete")
    print("=" * 70)
    print()
    print("次のステップ / Next Steps:")
    print("1. morioka_paddy_map_2025.html をブラウザで開く")
    print("   Open morioka_paddy_map_2025.html in a web browser")
    print("2. レイヤーパネルで各レイヤーを切り替えて確認")
    print("   Toggle layers in the layer panel to examine results")
    print("3. morioka_paddy_detection_2025.py で詳細な面積計算")
    print("   Run morioka_paddy_detection_2025.py for detailed area calculation")
    print()


if __name__ == "__main__":
    main()
