# Citation Verification Tool

論文ドラフトの引用を元論文PDFと照合し、誤引用・誇張・逆の結果を検出するツール。

## 機能

- **引用検出**: 複数の引用スタイル（APA, MLA, Vancouver, 番号形式など）を自動認識
- **PDFマッチング**: Zoteroフォルダ内のPDFと引用情報を自動マッチング
- **誤引用検出**: 元論文との内容比較で問題を検出
  - 誇張 (exaggerated): 元論文より強い表現を使用
  - 逆の結果 (reversed): 結論が元論文と逆
  - 誤引用 (misquoted): 数値や内容が異なる
  - 根拠なし (unsupported): 元論文で確認できない
- **レポート生成**: Markdown/JSON/コンソール形式で結果を出力

## インストール

```bash
pip install pymupdf  # PDF解析用（必須）
pip install google-auth-oauthlib google-api-python-client  # Google Drive用（オプション）
```

## 使い方

### 基本的な使い方（Pythonから）

```python
from citation_verifier import quick_check, verify_citations

# 引用を検出
text = '''
先行研究では、ディープラーニングは常に従来手法を上回ることが
示されている (Smith, 2020)。この結果は決定的であり、
例外はないとされている (Jones et al., 2019)。
'''

# 簡易チェック（PDFマッチングなし）
print(quick_check(text))

# 詳細検証（PDFマッチングあり）
result = verify_citations(
    text,
    zotero_path="/path/to/Zotero/storage"
)
print(result)
```

### 特定の主張をPDFと照合

```python
from citation_verifier import analyze_claim

result = analyze_claim(
    claim="この手法は常に99%以上の精度を達成する",
    source_pdf_path="/path/to/paper.pdf",
    keywords=["accuracy", "precision"]  # オプション
)

print(f"ステータス: {result['status_label']}")
print(f"信頼度: {result['confidence']:.0%}")

for issue in result['issues']:
    print(f"- {issue['description']}")
```

### CLIから使用

```bash
# 簡易チェック
python -m citation_verifier check -t "引用を含むテキスト..."

# 詳細検証
python -m citation_verifier verify -f draft.txt --zotero-path /path/to/Zotero/storage

# 設定確認
python -m citation_verifier config
```

### Google Drive連携

1. Google Cloud Consoleでプロジェクトを作成
2. Drive APIを有効化
3. OAuth 2.0認証情報を作成してダウンロード

```python
from citation_verifier import CitationVerificationTool

tool = CitationVerificationTool(
    use_google_drive=True,
    credentials_path="/path/to/credentials.json",
    zotero_folder_id="YOUR_ZOTERO_FOLDER_ID"
)

result = tool.verify_text(draft_text)
```

## 検出される問題タイプ

| ステータス | 説明 | 深刻度 |
|-----------|------|--------|
| accurate | 正確な引用 | - |
| exaggerated | 元論文より強い表現 | 中 |
| reversed | 結論が逆 | 高 |
| misquoted | 数値・内容が異なる | 高 |
| unsupported | 根拠が見つからない | 高 |
| partial | 部分的に正確 | 中 |
| unverifiable | 検証不可能 | 低 |

## 対応する引用スタイル

- **APA**: (Author, 2020), Author (2020), (Author et al., 2020)
- **MLA**: (Author 123)
- **Vancouver**: [1], [2], [1-3]
- **番号形式**: (1), (2), 1)
- **脚注**: [^1], ¹, ²

## 設定ファイル

設定は `~/.citation_verifier/config.json` に保存されます:

```json
{
  "zotero_local_path": "/Users/you/Zotero/storage",
  "google_drive_credentials_path": "/path/to/credentials.json",
  "zotero_folder_id": "FOLDER_ID",
  "cache_dir": "~/.citation_verifier/cache",
  "similarity_threshold": 0.7
}
```

## アーキテクチャ

```
citation_verifier/
├── __init__.py       # パッケージ初期化・APIエクスポート
├── api.py            # シンプルAPI
├── main.py           # メインCLIツール
├── config.py         # 設定管理
├── citation_parser.py # 引用パース
├── pdf_parser.py     # PDF解析
├── matcher.py        # 引用-PDFマッチング
├── verifier.py       # 引用検証ロジック
└── reporter.py       # レポート生成
```

## ライセンス

MIT License
