#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
岩手県水田マップ可視化スクリプト / Iwate Paddy Field Map Visualization Script

このスクリプトは、検出された水田をインタラクティブなマップとして可視化します。
This script visualizes detected paddy fields as an interactive map.
"""

import ee
import folium


def initialize_ee():
    """Google Earth Engineの初期化 / Initialize Google Earth Engine"""
    try:
        ee.Initialize()
        print("✓ Google Earth Engine initialized successfully")
        return True
    except Exception as e:
        print("Google Earth Engine initialization failed.")
        print("Please run: earthengine authenticate")
        print(f"Error: {e}")
        return False


def add_ee_layer(map_object, ee_image_object, vis_params, name):
    """
    Foliumマップにアース・エンジン・レイヤーを追加
    Add Earth Engine layer to Folium map
    """
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=name,
        overlay=True,
        control=True
    ).add_to(map_object)


def create_visualization_map():
    """
    可視化マップの作成 / Create visualization map
    """
    print("Creating interactive visualization map...")

    # 岩手県の中心座標 / Iwate Prefecture center coordinates
    iwate_center = [39.5, 141.5]

    # Foliumマップの作成 / Create Folium map
    map_iwate = folium.Map(
        location=iwate_center,
        zoom_start=9,
        tiles='OpenStreetMap'
    )

    # 岩手県の境界を取得 / Get Iwate Prefecture boundary
    japan = ee.FeatureCollection("FAO/GAUL/2015/level1")
    iwate = japan.filter(ee.Filter.And(
        ee.Filter.eq('ADM0_NAME', 'Japan'),
        ee.Filter.eq('ADM1_NAME', 'Iwate')
    ))

    # もし境界が取得できない場合の代替
    if iwate.size().getInfo() == 0:
        print("Using approximate coordinates for Iwate Prefecture")
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

    # 境界を追加 / Add boundary
    style_function = lambda x: {'fillColor': 'none', 'color': 'red', 'weight': 2}
    folium.GeoJson(
        iwate.getInfo(),
        name='Iwate Prefecture Boundary',
        style_function=style_function
    ).add_to(map_iwate)

    # Sentinel-2 画像を追加 / Add Sentinel-2 image
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(iwate) \
        .filterDate('2024-06-01', '2024-08-31') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
        .median()

    # True Color 可視化 / True Color visualization
    vis_params_rgb = {
        'min': 0,
        'max': 3000,
        'bands': ['B4', 'B3', 'B2']
    }

    add_ee_layer(map_iwate, s2, vis_params_rgb, 'Sentinel-2 RGB')

    # NDVI 可視化 / NDVI visualization
    ndvi = s2.normalizedDifference(['B8', 'B4'])
    vis_params_ndvi = {
        'min': -0.2,
        'max': 0.8,
        'palette': ['blue', 'white', 'green']
    }

    add_ee_layer(map_iwate, ndvi, vis_params_ndvi, 'NDVI')

    # レイヤーコントロールを追加 / Add layer control
    folium.LayerControl().add_to(map_iwate)

    # マップをHTMLファイルとして保存 / Save map as HTML file
    output_file = 'iwate_paddy_map.html'
    map_iwate.save(output_file)
    print(f"✓ Map saved to: {output_file}")
    print(f"  Open this file in your web browser to view the interactive map")

    return output_file


def main():
    """メイン処理 / Main processing"""
    print("=" * 60)
    print("岩手県水田マップ可視化")
    print("Iwate Paddy Field Map Visualization")
    print("=" * 60)
    print()

    if not initialize_ee():
        return

    create_visualization_map()

    print()
    print("=" * 60)
    print("可視化完了 / Visualization Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
