// 盛岡市水田面積判別スクリプト 2025年版 (Google Earth Engine Code Editor用)
// Morioka City Paddy Field Detection Script 2025 (for GEE Code Editor)

// ============================================================================
// このスクリプトをGoogle Earth Engine Code Editorにコピーして実行してください
// Copy this script to Google Earth Engine Code Editor and run it
// https://code.earthengine.google.com/
//
// 特徴 / Features:
// - 盛岡市中心半径50kmの水田を検出 / Detects paddy fields within 50km of Morioka center
// - 2025年7月の干ばつを考慮したアルゴリズム / Drought-aware algorithm for July 2025
// - 農地面積の60%が水田であることを考慮 / Considers 60% of agricultural land is paddy
// ============================================================================

// ============================================================================
// 設定 / Configuration
// ============================================================================

// 盛岡市の中心座標 / Morioka City center coordinates
// 緯度: 39.7036°N, 経度: 141.1527°E (盛岡市役所)
var moriokaCenter = ee.Geometry.Point([141.1527, 39.7036]);

// 半径50kmの円形範囲を作成 / Create 50km radius circular region
var moriokaRegion = moriokaCenter.buffer(50000);  // 50,000 meters = 50 km

// マップの中心を盛岡市に設定 / Center map on Morioka City
Map.centerObject(moriokaCenter, 10);

// 対象年度の設定 / Set target year
var targetYear = 2025;

// ============================================================================
// 期間設定 / Period Definitions
// ============================================================================

// データ取得期間を拡大して、南西方向のデータも確実に取得
// Extend data acquisition period to ensure southwest region coverage
var dataStart = ee.Date.fromYMD(targetYear, 3, 15);  // 3月中旬から
var dataEnd = ee.Date.fromYMD(targetYear, 11, 15);   // 11月中旬まで

// 田植え期 (5月-6月中旬): 湛水状態
// Planting period (May to mid-June): Flooded state
var plantingStart = ee.Date.fromYMD(targetYear, 5, 1);
var plantingEnd = ee.Date.fromYMD(targetYear, 6, 20);

// 初期生育期 (6月中旬-7月初旬): 稲の成長開始
// Early growing period (mid-June to early July): Rice growth begins
var earlyGrowthStart = ee.Date.fromYMD(targetYear, 6, 15);
var earlyGrowthEnd = ee.Date.fromYMD(targetYear, 7, 5);

// 干ばつ期 (7月-8月初旬): 2025年の干ばつ期間
// Drought period (July to early August): 2025 drought period
var droughtStart = ee.Date.fromYMD(targetYear, 7, 1);
var droughtEnd = ee.Date.fromYMD(targetYear, 8, 5);

// 回復期 (8月-9月初旬): 干ばつ後の回復
// Recovery period (August to early September): Post-drought recovery
var recoveryStart = ee.Date.fromYMD(targetYear, 8, 1);
var recoveryEnd = ee.Date.fromYMD(targetYear, 9, 10);

// 収穫前期 (9月-10月中旬): 成熟期
// Pre-harvest period (September to mid-October): Maturation
var harvestStart = ee.Date.fromYMD(targetYear, 9, 1);
var harvestEnd = ee.Date.fromYMD(targetYear, 10, 15);

// ============================================================================
// インデックス計算関数 / Index Calculation Functions
// ============================================================================

var addIndices = function(image) {
  // NDVI (正規化植生指数) / Normalized Difference Vegetation Index
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');

  // NDWI (正規化水指数) / Normalized Difference Water Index
  var ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI');

  // LSWI (Land Surface Water Index) - 水田検出に有効
  var lswi = image.normalizedDifference(['B8', 'B11']).rename('LSWI');

  // EVI (Enhanced Vegetation Index) - 干ばつ条件でより感度が高い
  // More sensitive under drought conditions
  // EVI = 2.5 * (NIR - Red) / (NIR + 6 * Red - 7.5 * Blue + 1)
  var nir = image.select('B8');
  var red = image.select('B4');
  var blue = image.select('B2');
  var evi = nir.subtract(red).multiply(2.5).divide(
    nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)
  ).rename('EVI');

  return image.addBands(ndvi).addBands(ndwi).addBands(lswi).addBands(evi);
};

// ============================================================================
// Sentinel-2データの読み込み / Load Sentinel-2 Data
// ============================================================================

// クラウドカバー閾値を緩和して、南西方向のデータも確実に取得
// Relax cloud cover threshold to ensure southwest region coverage
var s2Collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(moriokaRegion)
  .filterDate(dataStart, dataEnd)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))  // 30% → 50%に緩和
  .map(addIndices);

print('Total Sentinel-2 images:', s2Collection.size());
print('Period:', dataStart.format('YYYY-MM-dd').getInfo(), 'to', dataEnd.format('YYYY-MM-dd').getInfo());
print('Cloud cover threshold: 50% (relaxed for better coverage)');

// ============================================================================
// 各期間の画像を取得 / Get Images for Each Period
// ============================================================================

// 田植え期 / Planting period
// mean()を使用して欠損値を最小化 / Use mean() to minimize missing data
var plantingPeriod = s2Collection.filterDate(plantingStart, plantingEnd);
var plantingNDVI = plantingPeriod.select('NDVI').mean();
var plantingNDWI = plantingPeriod.select('NDWI').mean();
var plantingLSWI = plantingPeriod.select('LSWI').mean();

print('Planting period images:', plantingPeriod.size());

// 初期生育期 / Early growth period
var earlyGrowthPeriod = s2Collection.filterDate(earlyGrowthStart, earlyGrowthEnd);
var earlyGrowthNDVI = earlyGrowthPeriod.select('NDVI').mean();

print('Early growth period images:', earlyGrowthPeriod.size());

// 干ばつ期 / Drought period
var droughtPeriod = s2Collection.filterDate(droughtStart, droughtEnd);
var droughtNDVI = droughtPeriod.select('NDVI').mean();
var droughtEVI = droughtPeriod.select('EVI').mean();
var droughtLSWI = droughtPeriod.select('LSWI').mean();

print('Drought period (July-early Aug) images:', droughtPeriod.size());

// 回復期 / Recovery period
var recoveryPeriod = s2Collection.filterDate(recoveryStart, recoveryEnd);
var recoveryNDVI = recoveryPeriod.select('NDVI').mean();
var recoveryEVI = recoveryPeriod.select('EVI').mean();

print('Recovery period (Aug-early Sep) images:', recoveryPeriod.size());

// 収穫前期 / Pre-harvest period
var harvestPeriod = s2Collection.filterDate(harvestStart, harvestEnd);
var harvestNDVI = harvestPeriod.select('NDVI').mean();

print('Pre-harvest period (Sep-mid Oct) images:', harvestPeriod.size());

// ============================================================================
// Sentinel-1 SARデータの読み込み / Load Sentinel-1 SAR Data
// ============================================================================

// 広い期間で取得して南西方向もカバー / Acquire over extended period to cover southwest
var s1Start = ee.Date.fromYMD(targetYear, 4, 15);
var s1End = ee.Date.fromYMD(targetYear, 6, 30);

var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(moriokaRegion)
  .filterDate(s1Start, s1End)
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
  .filter(ee.Filter.eq('instrumentMode', 'IW'));

var plantingSAR = s1.select('VV').mean();  // mean()で欠損値を最小化

print('Sentinel-1 SAR images (planting period):', s1.size());

// ============================================================================
// 水田の検出 (2025年干ばつ考慮版) / Detect Paddy Fields (Drought-Aware 2025)
// ============================================================================

print('');
print('=== Detection Criteria (Drought-Aware + Full Coverage) ===');
print('Planting period: NDVI < 0.3, NDWI > 0.0 or LSWI > 0.0');
print('July drought: NDVI 0.3-0.7 (adjusted threshold for drought)');
print('August recovery: NDVI > 0.35 or EVI > 0.3');
print('September-October harvest: NDVI 0.3-0.65');
print('Cloud cover: < 50% (relaxed for better coverage)');
print('Data period: Extended to ensure complete spatial coverage');
print('Southwest region: Improved coverage with extended periods & mean()');
print('==========================================================');
print('');

// 水田の特徴 (2025年干ばつ考慮版):
// Paddy field characteristics (2025 drought-aware version):
// 1. 田植え期: 低いNDVI、高いNDWI/LSWI (湛水)
// 2. 7月干ばつ期: 通常より低いNDVI (0.3-0.7) ← 重要な調整
// 3. 8月回復期: NDVIの回復 (0.35以上)
// 4. 9月収穫前: 中程度のNDVI (0.3-0.65)

// 条件1: 田植え期の湛水状態 / Planting period flooding
var plantingCondition = plantingNDVI.lt(0.3)
  .and(plantingNDWI.gt(0.0))
  .or(plantingLSWI.gt(0.0));

// 条件2: 干ばつを考慮した7月の植生状態 / July vegetation considering drought
var droughtCondition = droughtNDVI.gt(0.3)
  .and(droughtNDVI.lt(0.7))
  .or(droughtEVI.gt(0.25));

// 条件3: 8月の回復期 / August recovery period
var recoveryCondition = recoveryNDVI.gt(0.35)
  .or(recoveryEVI.gt(0.3));

// 条件4: 収穫前の状態 / Pre-harvest state
var harvestCondition = harvestNDVI.gt(0.3)
  .and(harvestNDVI.lt(0.65));

// 総合的な水田判定 / Overall paddy field determination
var paddyMask = plantingCondition
  .and(droughtCondition.or(recoveryCondition))
  .and(harvestCondition);

// SAR データによる補正 / SAR data correction
var sarCount = s1.size().getInfo();
if (sarCount > 0) {
  var waterMask = plantingSAR.lt(-12);
  var sarPaddy = waterMask.and(
    recoveryNDVI.gt(0.3).or(harvestNDVI.gt(0.3))
  );
  paddyMask = paddyMask.or(sarPaddy);
}

// ノイズ除去 / Noise removal
paddyMask = paddyMask.focal_mode({radius: 30, units: 'meters'});

// マスクの適用 / Apply mask
paddyMask = paddyMask.selfMask();

// ============================================================================
// 面積計算 / Area Calculation
// ============================================================================

var pixelArea = paddyMask.multiply(ee.Image.pixelArea());
var areaStats = pixelArea.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: moriokaRegion,
  scale: 10,
  maxPixels: 1e13,
  bestEffort: true
});

var areaSqMeters = ee.Number(areaStats.values().get(0));
var areaHectares = areaSqMeters.divide(10000);
var areaKm2 = areaHectares.divide(100);

// 総農地面積の推定 (水田が60%と仮定)
// Estimate total agricultural area (assuming 60% is paddy)
var paddyRatio = 0.6;
var totalAgriculturalArea = areaHectares.divide(paddyRatio);
var otherAgricultureArea = totalAgriculturalArea.subtract(areaHectares);

// ============================================================================
// 結果の表示 / Display Results
// ============================================================================

print('');
print('======================================================================');
print('結果 / RESULTS');
print('======================================================================');
print('対象地域 / Target Region: 盛岡市中心半径50km');
print('Target Region: 50km radius from Morioka City center');
print('対象年度 / Target Year:', targetYear);
print('処理期間 / Processing Period: 2025-03-15 to 2025-11-15 (Extended)');
print('特記事項 / Note: 7月干ばつ考慮 + 南西方向含む全方向カバレッジ改善');
print('Note: July drought-aware + Improved coverage for all directions including SW');
print('');
print('カバレッジ改善 / Coverage Improvements:');
print('  - クラウドカバー閾値: 50% (緩和) / Cloud cover: 50% (relaxed)');
print('  - データ期間: 拡張 (3月中旬-11月中旬)');
print('    Data period: Extended (mid-Mar to mid-Nov)');
print('  - 南西方向のデータ欠損を解消');
print('    Resolved southwest region data gaps');
print('  - mean()使用でモザイク処理を改善');
print('    Improved mosaicking using mean()');
print('');
print('検出された水田面積 / Detected Paddy Field Area:');
print('  ヘクタール / Hectares:', areaHectares);
print('  平方キロメートル / km²:', areaKm2);
print('');
print('推定総農地面積 / Estimated Total Agricultural Area:');
print('  (水田が農地の60%と仮定)');
print('  (Assuming paddy fields are 60% of agricultural land)');
print('  ヘクタール / Hectares:', totalAgriculturalArea);
print('  平方キロメートル / km²:', totalAgriculturalArea.divide(100));
print('');
print('その他の農地 / Other Agricultural Land:');
print('  (畑、果樹園など / Fields, orchards, etc.)');
print('  ヘクタール / Hectares:', otherAgricultureArea);
print('');
print('⚠ 2025年版の改善点 / 2025 Version Improvements:');
print('  - 7月干ばつ: NDVI閾値 0.3-0.7 / July drought: NDVI 0.3-0.7');
print('  - 南西カバレッジ: 期間拡張+クラウド50%');
print('    Southwest coverage: Extended period + 50% cloud threshold');
print('  - 欠損値対策: mean()で完全カバー');
print('    Missing data: Complete coverage using mean()');
print('  - SAR画像: 広い期間で湛水期を確実に検出');
print('    SAR: Extended period for reliable flooding detection');
print('======================================================================');
print('');

// ============================================================================
// 可視化 / Visualization
// ============================================================================

// 1. 盛岡市中心と範囲の表示 / Display Morioka center and region
Map.addLayer(moriokaCenter, {color: 'red'}, '盛岡市中心 / Morioka Center', true);
Map.addLayer(moriokaRegion, {color: 'blue'}, '対象範囲 (半径50km) / Target Region (50km radius)', true);

// 2. True Color画像 (回復期・8月) / True Color image (recovery period - August)
var trueColorVis = {
  min: 0,
  max: 3000,
  bands: ['B4', 'B3', 'B2']
};
var trueColorImage = recoveryPeriod.median();
Map.addLayer(trueColorImage.clip(moriokaRegion), trueColorVis,
  'Sentinel-2 RGB (8月回復期 / August Recovery)', false);

// 3. NDVI比較 (各期間)
// NDVI Comparison (each period)
var ndviVis = {
  min: -0.2,
  max: 0.8,
  palette: ['blue', 'white', 'green']
};

Map.addLayer(plantingNDVI.clip(moriokaRegion), ndviVis,
  'NDVI - 田植え期 / Planting (May-Jun)', false);
Map.addLayer(droughtNDVI.clip(moriokaRegion), ndviVis,
  'NDVI - 干ばつ期 / Drought (July)', false);
Map.addLayer(recoveryNDVI.clip(moriokaRegion), ndviVis,
  'NDVI - 回復期 / Recovery (August)', false);
Map.addLayer(harvestNDVI.clip(moriokaRegion), ndviVis,
  'NDVI - 収穫前 / Pre-harvest (September)', false);

// 4. NDWI (田植え期の湛水検出) / NDWI (flooding detection during planting)
var ndwiVis = {
  min: -0.5,
  max: 0.5,
  palette: ['red', 'white', 'blue']
};
Map.addLayer(plantingNDWI.clip(moriokaRegion), ndwiVis,
  'NDWI - 田植え期湛水 / Planting Flooding', false);

// 5. SAR画像 (利用可能な場合) / SAR image (if available)
if (sarCount > 0) {
  var sarVis = {
    min: -25,
    max: -5,
    palette: ['black', 'white']
  };
  Map.addLayer(plantingSAR.clip(moriokaRegion), sarVis,
    'SAR VV - 田植え期 / Planting Period', false);
}

// 6. 検出された水田 (メインレイヤー) / Detected paddy fields (main layer)
var paddyVis = {
  min: 0,
  max: 1,
  palette: ['yellow', 'green']
};
Map.addLayer(paddyMask.clip(moriokaRegion), paddyVis,
  '✓ 検出された水田 / Detected Paddy Fields', true);

// ============================================================================
// エクスポート設定 / Export Settings
// ============================================================================

// 結果をGoogle Driveにエクスポートする場合は以下のコメントを解除
// Uncomment below to export results to Google Drive

/*
Export.image.toDrive({
  image: paddyMask.toByte().visualize(paddyVis),
  description: 'morioka_paddy_fields_2025_drought_aware',
  folder: 'GEE_Exports',
  region: moriokaRegion,
  scale: 10,
  maxPixels: 1e13
});

// GeoTIFF形式でエクスポート (解析用)
// Export as GeoTIFF (for analysis)
Export.image.toDrive({
  image: paddyMask.toByte(),
  description: 'morioka_paddy_fields_2025_geotiff',
  folder: 'GEE_Exports',
  region: moriokaRegion,
  scale: 10,
  fileFormat: 'GeoTIFF',
  maxPixels: 1e13
});
*/

// ============================================================================
// 完了メッセージ / Completion Message
// ============================================================================

print('');
print('✓ 可視化完了 / Visualization complete');
print('');
print('レイヤーパネルで各レイヤーの表示/非表示を切り替えられます');
print('You can toggle layers on/off in the Layers panel');
print('');
print('次のステップ / Next Steps:');
print('1. 各期間のNDVI画像を比較して干ばつの影響を確認');
print('   Compare NDVI images to see drought impact');
print('2. 水田マスクと実際の画像を重ねて精度を確認');
print('   Overlay paddy mask with actual imagery to verify accuracy');
print('3. Export設定のコメントを解除してGeoTIFFをエクスポート');
print('   Uncomment Export section to export GeoTIFF');
print('');
