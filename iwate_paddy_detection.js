// ==========================================
// 岩手県水田検出システム（複数年対応版）
// Iwate Prefecture Paddy Field Detection System (Multi-Year)
// ==========================================

// ============================================================================
// このスクリプトをGoogle Earth Engine Code Editorにコピーして実行してください
// Copy this script to Google Earth Engine Code Editor and run it
// https://code.earthengine.google.com/
// ============================================================================

// ==========================================
// 1. 基本設定
// ==========================================

// 岩手県の境界を定義 / Define Iwate Prefecture boundary
// 座標は岩手県のおおよその範囲 / Coordinates are approximate bounds of Iwate
var iwateBounds = ee.Geometry.Polygon([
  [[140.5, 38.8], [142.0, 38.8], [142.0, 40.5], [140.5, 40.5], [140.5, 38.8]]
]);

// または、行政区画データから取得 / Or get from administrative boundaries
// var japan = ee.FeatureCollection("FAO/GAUL/2015/level1");
// var iwate = japan.filter(ee.Filter.and(
//   ee.Filter.eq('ADM0_NAME', 'Japan'),
//   ee.Filter.eq('ADM1_NAME', 'Iwate')
// ));
// var iwateBounds = iwate.geometry();

// マップの中心を岩手県に設定 / Center map on Iwate Prefecture
Map.centerObject(iwateBounds, 9);

// 対象年度の設定（2018-2025） / Set target years (2018-2025)
var years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];

// ==========================================
// 2. 補助関数の定義
// ==========================================

// インデックスを追加する関数 / Function to add indices
var addIndices = function(image) {
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI');
  var lswi = image.normalizedDifference(['B8', 'B11']).rename('LSWI');
  var mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI');
  return image.addBands([ndvi, ndwi, lswi, mndwi]);
};

// ==========================================
// 3. 単一年次の水田検出関数
// ==========================================

function detectPaddyForYear(year) {
  print('Processing year: ' + year);

  // 各期間の設定 / Define periods
  var plantingStart = ee.Date.fromYMD(year, 5, 1);
  var plantingEnd = ee.Date.fromYMD(year, 6, 30);
  var growingStart = ee.Date.fromYMD(year, 7, 1);
  var growingEnd = ee.Date.fromYMD(year, 8, 31);
  var harvestStart = ee.Date.fromYMD(year, 9, 1);
  var harvestEnd = ee.Date.fromYMD(year, 9, 30);

  // Sentinel-2データの読み込み / Load Sentinel-2 data
  var s2Collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(iwateBounds)
    .filterDate(plantingStart, harvestEnd)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
    .map(addIndices);

  // データ数を確認 / Check data availability
  var collectionSize = s2Collection.size();
  print('  Year ' + year + ' - Available images:', collectionSize);

  // 全期間の中央値をフォールバックとして使用 / Use full period median as fallback
  var fallbackImage = s2Collection.median();

  // 各期間の中央値画像を取得（データがない場合はフォールバック使用）
  // Get median images for each period (use fallback if no data)
  var plantingPeriod = s2Collection.filterDate(plantingStart, plantingEnd);
  var plantingNDVI = ee.Algorithms.If(
    plantingPeriod.size().gt(0),
    plantingPeriod.select('NDVI').median(),
    fallbackImage.select('NDVI')
  );
  var plantingNDWI = ee.Algorithms.If(
    plantingPeriod.size().gt(0),
    plantingPeriod.select('NDWI').median(),
    fallbackImage.select('NDWI')
  );
  var plantingLSWI = ee.Algorithms.If(
    plantingPeriod.size().gt(0),
    plantingPeriod.select('LSWI').median(),
    fallbackImage.select('LSWI')
  );
  var plantingMNDWI = ee.Algorithms.If(
    plantingPeriod.size().gt(0),
    plantingPeriod.select('MNDWI').median(),
    fallbackImage.select('MNDWI')
  );

  var growingPeriod = s2Collection.filterDate(growingStart, growingEnd);
  var growingNDVI = ee.Algorithms.If(
    growingPeriod.size().gt(0),
    growingPeriod.select('NDVI').median(),
    fallbackImage.select('NDVI')
  );

  var harvestPeriod = s2Collection.filterDate(harvestStart, harvestEnd);
  var harvestNDVI = ee.Algorithms.If(
    harvestPeriod.size().gt(0),
    harvestPeriod.select('NDVI').median(),
    fallbackImage.select('NDVI')
  );

  // 画像にキャスト / Cast to images
  plantingNDVI = ee.Image(plantingNDVI);
  plantingNDWI = ee.Image(plantingNDWI);
  plantingLSWI = ee.Image(plantingLSWI);
  plantingMNDWI = ee.Image(plantingMNDWI);
  growingNDVI = ee.Image(growingNDVI);
  harvestNDVI = ee.Image(harvestNDVI);

  // 水田の検出 / Detect paddy fields
  // 水田の特徴:
  // 1. 田植え期: 低いNDVI、高いNDWI/MNDWI (水面)
  // 2. 生育期: 高いNDVI (緑の稲)
  // 3. 収穫前: 中程度のNDVI
  var waterCondition = plantingNDWI.gt(-0.05)
    .or(plantingLSWI.gt(0.0))
    .or(plantingMNDWI.gt(-0.1));

  var vegetationCondition = growingNDVI.gt(0.4);

  var seasonalCondition = plantingNDVI.lt(0.35);

  var paddyMask = waterCondition
    .and(vegetationCondition)
    .and(seasonalCondition)
    .and(harvestNDVI.gt(0.3));

  // ノイズ除去 / Noise removal
  paddyMask = paddyMask.focal_mode({radius: 30, units: 'meters'});

  // マスクの適用 / Apply mask
  paddyMask = paddyMask.selfMask();

  return paddyMask.rename('paddy');
}

// ==========================================
// 4. 複数年次の処理
// ==========================================

print('=== 岩手県水田検出システム（2018-2025） ===');
print('=== Iwate Prefecture Paddy Detection System (2018-2025) ===');

// 各年次の水田検出を実行 / Execute paddy detection for each year
var paddyResults = [];
var areaResults = [];

years.forEach(function(year) {
  var paddyMask = detectPaddyForYear(year);

  // 面積計算 / Calculate area
  var pixelArea = paddyMask.multiply(ee.Image.pixelArea());
  var areaStats = pixelArea.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: iwateBounds,
    scale: 10,
    maxPixels: 1e13,
    bestEffort: true,
    tileScale: 2
  });

  var areaHectares = ee.Number(areaStats.get('paddy')).divide(10000);

  paddyResults.push({
    year: year,
    image: paddyMask
  });

  // 面積結果を評価して表示 / Evaluate and display area results
  areaHectares.evaluate(function(area) {
    print(year + '年 水田面積 / Year ' + year + ' Paddy Area (ha):', area);
  });
});

// ==========================================
// 5. 地図の可視化
// ==========================================

// 水田マスクの可視化設定 / Visualization settings for paddy mask
var paddyColors = {
  2018: '#8B0000', // Dark Red
  2019: '#FF4500', // Orange Red
  2020: '#FFA500', // Orange
  2021: '#FFD700', // Gold
  2022: '#ADFF2F', // Green Yellow
  2023: '#00FA9A', // Medium Spring Green
  2024: '#00CED1', // Dark Turquoise
  2025: '#1E90FF'  // Dodger Blue
};

// 各年次のレイヤーを追加 / Add layers for each year
paddyResults.forEach(function(result) {
  var year = result.year;
  var image = result.image;
  var isVisible = (year === 2024); // 2024年のみデフォルトで表示

  Map.addLayer(image.clip(iwateBounds), {
    palette: [paddyColors[year]],
    min: 0,
    max: 1
  }, year + '年 水田 / Year ' + year + ' Paddy', isVisible, 0.7);
});

// 岩手県の境界 / Iwate Prefecture boundary
Map.addLayer(iwateBounds, {color: 'red'}, '岩手県境界 / Iwate Boundary', true);

// ==========================================
// 6. 凡例の作成
// ==========================================

var legend = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '8px 15px',
    backgroundColor: 'white'
  }
});

var legendTitle = ui.Label({
  value: '年次別水田検出 / Annual Paddy Detection',
  style: {
    fontWeight: 'bold',
    fontSize: '16px',
    margin: '0 0 8px 0'
  }
});

legend.add(legendTitle);

years.forEach(function(year) {
  var colorBox = ui.Label({
    style: {
      backgroundColor: paddyColors[year],
      padding: '8px',
      margin: '0 8px 0 0'
    }
  });

  var description = ui.Label({
    value: year + '年 / Year ' + year,
    style: {margin: '0 0 4px 6px'}
  });

  legend.add(
    ui.Panel({
      widgets: [colorBox, description],
      layout: ui.Panel.Layout.Flow('horizontal')
    })
  );
});

Map.add(legend);

// ==========================================
// 7. GeoTIFFエクスポート設定
// ==========================================

print('');
print('=== エクスポート準備完了 / Export Ready ===');
print('Tasksタブから以下のファイルを実行できます:');
print('You can run the following exports from the Tasks tab:');

paddyResults.forEach(function(result) {
  var year = result.year;
  var image = result.image;

  Export.image.toDrive({
    image: image.byte(),
    description: 'Iwate_Paddy_' + year,
    folder: 'GEE_exports',
    fileNamePrefix: 'iwate_paddy_' + year,
    region: iwateBounds,
    scale: 10,
    crs: 'EPSG:4326',
    fileFormat: 'GeoTIFF',
    maxPixels: 1e13
  });

  print('  ' + year + ': iwate_paddy_' + year + '.tif');
});

// ==========================================
// 8. 完了メッセージ
// ==========================================

print('');
print('✓ 処理完了 / Processing complete');
print('レイヤーパネルで各年次の表示/非表示を切り替えられます');
print('You can toggle each year on/off in the Layers panel');
