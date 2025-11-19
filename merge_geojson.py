#!/usr/bin/env python3
"""
GeoJSONファイルをマージするスクリプト
複数のGeoJSONファイルを一つのFeatureCollectionにまとめます
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_geojson(file_path: str) -> Dict[str, Any]:
    """GeoJSONファイルを読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_geojson_files(input_dir: str, output_file: str) -> None:
    """
    指定ディレクトリ内の全GeoJSONファイルをマージする

    Args:
        input_dir: GeoJSONファイルが格納されているディレクトリ
        output_file: 出力するマージ済みGeoJSONファイルのパス
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"エラー: ディレクトリが見つかりません: {input_dir}")
        sys.exit(1)

    # GeoJSONファイルを検索
    geojson_files = list(input_path.glob('*.geojson')) + list(input_path.glob('*.json'))

    if not geojson_files:
        print(f"エラー: {input_dir} にGeoJSONファイルが見つかりません")
        sys.exit(1)

    print(f"見つかったGeoJSONファイル数: {len(geojson_files)}")

    # マージ用のFeatureCollectionを初期化
    merged_features = []
    total_features = 0

    # 各ファイルを処理
    for idx, geojson_file in enumerate(geojson_files, 1):
        try:
            print(f"処理中 ({idx}/{len(geojson_files)}): {geojson_file.name}")
            data = load_geojson(geojson_file)

            # FeatureCollectionの場合
            if data.get('type') == 'FeatureCollection':
                features = data.get('features', [])
                merged_features.extend(features)
                total_features += len(features)
                print(f"  - {len(features)} フィーチャーを追加")

            # 単一のFeatureの場合
            elif data.get('type') == 'Feature':
                merged_features.append(data)
                total_features += 1
                print(f"  - 1 フィーチャーを追加")

            else:
                print(f"  - 警告: 未対応の形式: {data.get('type')}")

        except Exception as e:
            print(f"  - エラー: {geojson_file.name} の読み込みに失敗: {e}")
            continue

    # マージ結果を作成
    merged_geojson = {
        "type": "FeatureCollection",
        "features": merged_features
    }

    # 出力
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_geojson, f, ensure_ascii=False, indent=2)

    print(f"\n完了!")
    print(f"総ファイル数: {len(geojson_files)}")
    print(f"総フィーチャー数: {total_features}")
    print(f"出力ファイル: {output_file}")
    print(f"ファイルサイズ: {output_path.stat().st_size / (1024*1024):.2f} MB")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <入力ディレクトリ> [出力ファイル]")
        print("\n例:")
        print(f"  python {sys.argv[0]} ./fude2025_03")
        print(f"  python {sys.argv[0]} ./fude2025_03 merged_output.geojson")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "merged_fude2025.geojson"

    print("=" * 60)
    print("GeoJSONファイルマージツール")
    print("=" * 60)
    print(f"入力ディレクトリ: {input_dir}")
    print(f"出力ファイル: {output_file}")
    print("=" * 60)
    print()

    merge_geojson_files(input_dir, output_file)


if __name__ == "__main__":
    main()
