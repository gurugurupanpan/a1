// 岩手県水田面積判別スクリプト (Google Earth Engine Code Editor用)
// Iwate Prefecture Paddy Field Detection Script (for GEE Code Editor)

// ============================================================================
// このスクリプトをGoogle Earth Engine Code Editorにコピーして実行してください
// Copy this script to Google Earth Engine Code Editor and run it
// https://code.earthengine.google.com/
// ============================================================================

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

// 対象年度の設定 / Set target year
var targetYear = 2024;

// 各期間の設定 / Define periods
var plantingStart = ee.Date.fromYMD(targetYear, 5, 1);
var plantingEnd = ee.Date.fromYMD(targetYear, 6, 30);
var growingStart = ee.Date.fromYMD(targetYear, 7, 1);
var growingEnd = ee.Date.fromYMD(targetYear, 8, 31);
var harvestStart = ee.Date.fromYMD(targetYear, 9, 1);
var harvestEnd = ee.Date.fromYMD(targetYear, 9, 30);

// インデックスを追加する関数 / Function to add indices
var addIndices = function(image) {
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI');
  var lswi = image.normalizedDifference(['B8', 'B11']).rename('LSWI');
  return image.addBands(ndvi).addBands(ndwi).addBands(lswi);
};

// Sentinel-2データの読み込み / Load Sentinel-2 data
var s2Collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(iwateBounds)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .map(addIndices);

print('Total Sentinel-2 images:', s2Collection.size());

// 各期間の中央値画像を取得 / Get median images for each period
var plantingPeriod = s2Collection.filterDate(plantingStart, plantingEnd);
var plantingNDVI = plantingPeriod.select('NDVI').median();
var plantingNDWI = plantingPeriod.select('NDWI').median();
var plantingLSWI = plantingPeriod.select('LSWI').median();

var growingPeriod = s2Collection.filterDate(growingStart, growingEnd);
var growingNDVI = growingPeriod.select('NDVI').median();

var harvestPeriod = s2Collection.filterDate(harvestStart, harvestEnd);
var harvestNDVI = harvestPeriod.select('NDVI').median();

print('Planting period images:', plantingPeriod.size());
print('Growing period images:', growingPeriod.select('NDVI').median());
print('Harvest period images:', harvestPeriod.size());

// Sentinel-1 SARデータの読み込み / Load Sentinel-1 SAR data
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(iwateBounds)
  .filterDate(plantingStart, plantingEnd)
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
  .filter(ee.Filter.eq('instrumentMode', 'IW'));

var s1Median = s1.select('VV').median();
print('Sentinel-1 SAR images:', s1.size());

// 水田の検出 / Detect paddy fields
// 水田の特徴:
// 1. 田植え期: 低いNDVI、高いNDWI (水面)
// 2. 生育期: 高いNDVI (緑の稲)
// 3. 収穫前: 中程度のNDVI
var paddyMask = plantingNDVI.lt(0.3)              // 田植え期の低NDVI
  .and(plantingNDWI.gt(0.0))                      // 田植え期の高NDWI
  .or(plantingLSWI.gt(0.0))                       // または高いLSWI
  .and(growingNDVI.gt(0.4))                       // 生育期の高NDVI
  .and(harvestNDVI.gt(0.3));                      // 収穫前の中程度のNDVI

// SAR データによる補正 / SAR data correction
if (s1.size().getInfo() > 0) {
  var waterMask = s1Median.lt(-15);
  paddyMask = paddyMask.or(waterMask.and(growingNDVI.gt(0.4)));
}

// ノイズ除去 / Noise removal
paddyMask = paddyMask.focal_mode({radius: 30, units: 'meters'});

// マスクの適用 / Apply mask
paddyMask = paddyMask.selfMask();

// 面積計算 / Calculate area
var pixelArea = paddyMask.multiply(ee.Image.pixelArea());
var areaStats = pixelArea.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: iwateBounds,
  scale: 10,
  maxPixels: 1e13
});

var areaSqMeters = areaStats.get('NDVI');
var areaHectares = ee.Number(areaSqMeters).divide(10000);

print('==================================================');
print('結果 / RESULTS');
print('==================================================');
print('検出された水田面積 / Detected Paddy Field Area:');
print('  ヘクタール / Hectares:', areaHectares);
print('  平方キロメートル / km²:', areaHectares.divide(100));
print('==================================================');

// 可視化 / Visualization

// True Color画像 (生育期) / True Color image (growing period)
var trueColorVis = {
  min: 0,
  max: 3000,
  bands: ['B4', 'B3', 'B2']
};
var trueColorImage = growingPeriod.median();
Map.addLayer(trueColorImage.clip(iwateBounds), trueColorVis, 'Sentinel-2 RGB (Growing Period)', false);

// NDVI (生育期) / NDVI (growing period)
var ndviVis = {
  min: -0.2,
  max: 0.8,
  palette: ['blue', 'white', 'green']
};
Map.addLayer(growingNDVI.clip(iwateBounds), ndviVis, 'NDVI (Growing Period)', false);

// 水田マスク / Paddy field mask
var paddyVis = {
  min: 0,
  max: 1,
  palette: ['yellow', 'green']
};
Map.addLayer(paddyMask.clip(iwateBounds), paddyVis, 'Detected Paddy Fields', true);

// 岩手県の境界 / Iwate Prefecture boundary
Map.addLayer(iwateBounds, {color: 'red'}, 'Iwate Boundary', true);

// エクスポート設定 (オプション) / Export settings (optional)
// 結果をGoogle Driveにエクスポートする場合は以下のコメントを解除
// Uncomment below to export results to Google Drive
/*
Export.image.toDrive({
  image: paddyMask.visualize(paddyVis),
  description: 'iwate_paddy_fields_' + targetYear,
  region: iwateBounds,
  scale: 10,
  maxPixels: 1e13
});
*/

print('✓ 可視化完了 / Visualization complete');
print('レイヤーパネルで各レイヤーの表示/非表示を切り替えられます');
print('You can toggle layers on/off in the Layers panel');
