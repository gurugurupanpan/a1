// 盛岡市周辺の土地利用分類図 - 水田抽出機能付き（2025年・干ばつ対応版）

// ============================================================================
// 修正点:
// 1. バッファサイズを20kmに設定
// 2. landCoverPaletteの定義を追加
// 3. 地図のズームレベルを調整
// ============================================================================

// ESA WorldCoverのカラーパレット定義
var landCoverPalette = [
  '#006400', // 10 - Tree cover
  '#ffbb22', // 20 - Shrubland
  '#ffff4c', // 30 - Grassland
  '#f096ff', // 40 - Cropland
  '#fa0000', // 50 - Built-up
  '#b4b4b4', // 60 - Bare / sparse vegetation
  '#f0f0f0', // 70 - Snow and ice
  '#0064c8', // 80 - Permanent water bodies
  '#0096a0', // 90 - Herbaceous wetland
  '#00cf75', // 95 - Mangroves
  '#fae6a0'  // 100 - Moss and lichen
];

// 盛岡市の座標とエリア設定
var morioka = ee.Geometry.Point([141.1527, 39.7036]);
var aoiBounds = morioka.buffer(20000); // 20km半径

// 対象期間の設定（水田の水張り期を含む）
var startDate = '2025-04-01';
var endDate = '2025-10-31';

// ESA WorldCover 2021（最新版）
var worldCover = ee.ImageCollection("ESA/WorldCover/v200")
  .first()
  .clip(aoiBounds);

// Sentinel-2画像コレクション（雲除去済み）
var s2 = ee.ImageCollection('COPERNICUS/S2_SR')
  .filterBounds(aoiBounds)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
  .map(function(image) {
    var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
    var ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI');
    var mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI');
    return image.addBands([ndvi, ndwi, mndwi]);
  });

// 利用可能な画像数を確認
print('利用可能なSentinel-2画像数:', s2.size());

// 月別コンポジット作成
var months = ee.List.sequence(4, 10); // 4月から10月
var monthlyComposites = months.map(function(month) {
  var filtered = s2.filter(ee.Filter.calendarRange(month, month, 'month'));
  var count = filtered.size();

  return ee.Algorithms.If(
    count.gt(0),
    filtered.median().set('month', month).set('count', count),
    ee.Image.constant([0, 0, 0]).rename(['NDVI', 'MNDWI', 'NDWI'])
      .set('month', month).set('count', 0)
  );
});
var monthlyCollection = ee.ImageCollection.fromImages(monthlyComposites);

// 各月の画像数を表示
print('月別画像数:', monthlyCollection.aggregate_array('count'));

// 農地マスク（ESA WorldCoverから）
var croplandMask = worldCover.eq(40);

// 地形条件（水田は平地に多い）
var elevation = ee.Image('USGS/SRTMGL1_003').clip(aoiBounds);
var slope = ee.Terrain.slope(elevation);
var flatAreas = slope.lt(5); // 5度未満の傾斜

// ==========================================
// 2025年7月干ばつ対応（降水量40mm = 平年の20%）
// 戦略: 7月を除外し、干ばつ前（4-6月）と干ばつ後（8-9月）を活用
// ==========================================

// 【重要】各時期の植生・水指数
// 干ばつ前期（4-6月）: 水張り～初期生育
var preDroughtNDVI = monthlyCollection
  .filter(ee.Filter.inList('month', [4, 5, 6]))
  .select('NDVI')
  .max();

var preDroughtMNDWI = monthlyCollection
  .filter(ee.Filter.inList('month', [4, 5, 6]))
  .select('MNDWI')
  .max();

// 7月（干ばつ期）: この期間のデータは使用しない
// ※7月は降水量40mm（平年197.5mmの20%）で稲が極度のストレス状態

// 干ばつ後期（8-9月）: 回復期～収穫前
var postDroughtNDVI = monthlyCollection
  .filter(ee.Filter.inList('month', [8, 9]))
  .select('NDVI')
  .max();

// 6月のNDVI（干ばつ直前の最良状態）
var juneNDVI = monthlyCollection
  .filter(ee.Filter.eq('month', 6))
  .select('NDVI')
  .median();


// 【手法1】春期の水張り + 干ばつ後の回復
// 論理: 春に水があり、干ばつ後に植生が回復していれば水田
var paddyMethod1 = preDroughtMNDWI.gt(-0.1)  // 0.0 → -0.1（さらに緩和）
  .and(postDroughtNDVI.gt(0.15))  // 0.25 → 0.15（大幅緩和）
  .and(croplandMask)
  .and(flatAreas);

// 【手法2】干ばつによる極端な落ち込みパターン
// 論理: 6月→8月で極端に落ち込む = 7月干ばつの影響 = 水田の特徴
var june8Decline = juneNDVI.subtract(
  monthlyCollection.filter(ee.Filter.eq('month', 8)).select('NDVI').median()
);

var paddyMethod2 = june8Decline.gt(0.05)  // 0.1 → 0.05（緩和）
  .and(preDroughtNDVI.gt(0.2))  // 0.3 → 0.2（緩和）
  .and(croplandMask)
  .and(flatAreas);

// 【手法3】春期重視（干ばつの影響を受けていない期間）
// 論理: 春に水田の典型的特徴（水+初期植生）があれば水田
var paddyMethod3 = preDroughtMNDWI.gt(-0.05)  // 0.05 → -0.05（大幅緩和）
  .and(preDroughtNDVI.gt(0.15).and(preDroughtNDVI.lt(0.7)))  // 0.25 → 0.15（緩和）
  .and(croplandMask)
  .and(flatAreas);

// 【手法4】NDVI時系列の高変動（4-10月全体）
// 論理: 干ばつで極端な変動 = 水稲栽培の痕跡
var ndviStdDev = monthlyCollection.select('NDVI').reduce(ee.Reducer.stdDev());
var paddyMethod4 = ndviStdDev.gt(0.08)  // 0.12 → 0.08（緩和）
  .and(croplandMask)
  .and(flatAreas);

// 【手法5】春の水 + わずかな干ばつ後植生
// 論理: 春に水があり、干ばつ後にわずかでも植生 = 生き残った水田
var paddyMethod5 = preDroughtMNDWI.gt(-0.15)  // -0.05 → -0.15（大幅緩和）
  .and(postDroughtNDVI.gt(0.1))  // 0.2 → 0.1（大幅緩和）
  .and(preDroughtNDVI.gt(0.15))  // 0.2 → 0.15（緩和）
  .and(croplandMask)
  .and(flatAreas);

// 【手法6】6月ピーク法（干ばつ直前の最良状態）
// 論理: 6月にピークがあり、その後低下 = 7月干ばつの影響
var paddyMethod6 = juneNDVI.gt(0.25)  // 0.35 → 0.25（大幅緩和）
  .and(preDroughtMNDWI.gt(-0.1))  // 0.0 → -0.1（緩和）
  .and(croplandMask)
  .and(flatAreas);

// 【手法7】農地マスク内の平地（追加）
// 論理: 農地で平地なら水田の可能性が高い（特に盛岡地域）
var paddyMethod7 = croplandMask
  .and(flatAreas)
  .and(preDroughtNDVI.gt(0.1))  // 最低限の植生
  .and(postDroughtNDVI.gt(0.05));  // 干ばつ後も何か残っている

// 【手法8】春に水の痕跡があればOK（最も緩い）
// 論理: 春に少しでも水があれば水田
var paddyMethod8 = preDroughtMNDWI.gt(-0.2)  // 極めて緩い閾値
  .and(croplandMask)
  .and(flatAreas)
  .and(preDroughtNDVI.gt(0.1).or(postDroughtNDVI.gt(0.1)));  // どちらかに植生

// 全手法を組み合わせ（いずれか1つ以上に該当すれば水田）
var methodSum = paddyMethod1.add(paddyMethod2).add(paddyMethod3)
  .add(paddyMethod4).add(paddyMethod5).add(paddyMethod6)
  .add(paddyMethod7).add(paddyMethod8);

var paddyFields = methodSum.gte(1);  // 1つ以上の手法で検出（かなり緩い）

// その他の農地（畑など）
var otherCropland = croplandMask.and(paddyFields.not());


// 地図の初期設定（ズームレベルを調整）
Map.centerObject(aoiBounds, 11); // 20km半径に最適化

// レイヤー追加
Map.addLayer(worldCover, {
  min: 10,
  max: 100,
  palette: landCoverPalette
}, '土地被覆分類 (ESA WorldCover 2021)', false);

// 農地全体
Map.addLayer(croplandMask.updateMask(croplandMask), {
  palette: ['#ffff00']
}, '農地全体', false, 0.5);

// 水田
Map.addLayer(paddyFields.updateMask(paddyFields), {
  palette: ['#00ffff']
}, '水田（高感度版）', true, 0.8);

// その他の農地（畑など）
Map.addLayer(otherCropland.updateMask(otherCropland), {
  palette: ['#ffa500']
}, 'その他の農地（畑など）', true, 0.6);

// 検証用：各手法の結果を個別表示
Map.addLayer(paddyMethod1.updateMask(paddyMethod1), {
  palette: ['#ff00ff']
}, '手法1: 春の水+干ばつ後回復', false);

Map.addLayer(paddyMethod2.updateMask(paddyMethod2), {
  palette: ['#00ff00']
}, '手法2: 6月→8月極端低下', false);

Map.addLayer(paddyMethod3.updateMask(paddyMethod3), {
  palette: ['#0000ff']
}, '手法3: 春期重視', false);

Map.addLayer(paddyMethod4.updateMask(paddyMethod4), {
  palette: ['#ffff00']
}, '手法4: NDVI高変動', false);

Map.addLayer(paddyMethod5.updateMask(paddyMethod5), {
  palette: ['#ff9900']
}, '手法5: 緩和版', false);

Map.addLayer(paddyMethod6.updateMask(paddyMethod6), {
  palette: ['#ff0000']
}, '手法6: 6月ピーク法', false);

Map.addLayer(paddyMethod7.updateMask(paddyMethod7), {
  palette: ['#00ffff']
}, '手法7: 平地農地', false);

Map.addLayer(paddyMethod8.updateMask(paddyMethod8), {
  palette: ['#ff00aa']
}, '手法8: 超緩和版', false);

Map.addLayer(methodSum, {
  min: 0,
  max: 8,
  palette: ['white', 'yellow', 'orange', 'red', 'darkred', 'purple', 'black', 'navy', 'darkblue']
}, '手法重複度（色が濃いほど確実）', false);

// 検証用：季節変化の可視化
Map.addLayer(preDroughtMNDWI, {
  min: -0.3,
  max: 0.5,
  palette: ['brown', 'white', 'blue']
}, '春期の水指数 (MNDWI 4-6月)', false);

Map.addLayer(preDroughtNDVI, {
  min: 0,
  max: 0.8,
  palette: ['white', 'yellow', 'green', 'darkgreen']
}, '干ばつ前の植生 (NDVI 4-6月)', false);

Map.addLayer(juneNDVI, {
  min: 0,
  max: 0.8,
  palette: ['white', 'yellow', 'green', 'darkgreen']
}, '6月NDVI（干ばつ直前）', false);

Map.addLayer(postDroughtNDVI, {
  min: 0,
  max: 0.8,
  palette: ['white', 'yellow', 'orange', 'red']
}, '干ばつ後の植生 (NDVI 8-9月)', false);

Map.addLayer(june8Decline, {
  min: -0.2,
  max: 0.5,
  palette: ['blue', 'white', 'yellow', 'orange', 'red']
}, '6月→8月の低下量', false);

Map.addLayer(ndviStdDev, {
  min: 0,
  max: 0.3,
  palette: ['white', 'yellow', 'orange', 'red']
}, 'NDVI標準偏差（季節変動）', false);

// 盛岡市の位置
Map.addLayer(morioka, {color: 'red'}, '盛岡市中心部');

// AOIの境界を表示（解析範囲を確認）
Map.addLayer(aoiBounds, {color: 'blue'}, '解析範囲（20km半径）', true);

// 面積計算
var paddyArea = paddyFields.multiply(ee.Image.pixelArea()).rename('area');
var otherCropArea = otherCropland.multiply(ee.Image.pixelArea()).rename('area');

var paddyStats = paddyArea.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: aoiBounds,
  scale: 10,
  maxPixels: 1e13
});

var otherCropStats = otherCropArea.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: aoiBounds,
  scale: 10,
  maxPixels: 1e13
});

// 結果出力
print('==================================================');
print('盛岡市周辺（20km圏内）の解析結果');
print('==================================================');
print('盛岡市周辺（20km圏内）の水田面積 (m²):', paddyStats);
print('盛岡市周辺（20km圏内）のその他農地面積 (m²):', otherCropStats);

// ヘクタールに変換して表示
var paddyHa = ee.Number(paddyStats.get('area')).divide(10000);
var otherHa = ee.Number(otherCropStats.get('area')).divide(10000);
print('水田面積 (ha):', paddyHa);
print('その他農地面積 (ha):', otherHa);

// 割合計算
var totalCroplandArea = croplandMask.multiply(ee.Image.pixelArea()).rename('area');
var totalCropStats = totalCroplandArea.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: aoiBounds,
  scale: 10,
  maxPixels: 1e13
});

var totalCropHa = ee.Number(totalCropStats.get('area')).divide(10000);
var paddyRatio = paddyHa.divide(totalCropHa).multiply(100);
print('全農地面積 (ha):', totalCropHa);
print('水田の割合 (%):', paddyRatio);
print('==================================================');

// 平方キロメートルでも表示
var paddyKm2 = paddyHa.divide(100);
var totalCropKm2 = totalCropHa.divide(100);
print('水田面積 (km²):', paddyKm2);
print('全農地面積 (km²):', totalCropKm2);
print('==================================================');

print('✓ スクリプト実行完了');
print('※ 解析範囲は20km半径に設定されています');
print('※ 地図上の青い円が解析範囲を示しています');
