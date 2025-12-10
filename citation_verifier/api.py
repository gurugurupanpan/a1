"""
Citation Verification Tool - シンプルAPI
Claudeチャットからの使用を想定したシンプルなインターフェース
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from .main import CitationVerificationTool
from .citation_parser import CitationParser, extract_citations
from .verifier import CitationVerifier, VerificationStatus


def verify_citations(
    text: str,
    zotero_path: Optional[str] = None,
    reference_list: Optional[str] = None,
    output_format: str = "markdown"
) -> str:
    """
    論文テキスト内の引用を検証する

    使用例:
    ```python
    from citation_verifier import verify_citations

    draft = '''
    先行研究では、ディープラーニングは常に従来手法を上回ることが
    示されている (Smith, 2020)。この結果は決定的であり、
    例外はないとされている。
    '''

    result = verify_citations(
        draft,
        zotero_path="/path/to/Zotero/storage"
    )
    print(result)
    ```

    Args:
        text: 検証する論文テキスト
        zotero_path: Zoteroストレージのパス
        reference_list: 参考文献リスト（番号引用の場合）
        output_format: 出力形式 ("markdown", "json", "console")

    Returns:
        検証レポート
    """
    tool = CitationVerificationTool(zotero_path=zotero_path)
    return tool.verify_text(text, reference_list, output_format)


def quick_check(text: str) -> str:
    """
    引用の簡易チェック（PDFマッチングなし）

    使用例:
    ```python
    from citation_verifier import quick_check

    text = "This was shown by Smith (2020) and Jones et al. (2019)."
    print(quick_check(text))
    ```

    Args:
        text: チェックするテキスト

    Returns:
        検出された引用のリスト
    """
    tool = CitationVerificationTool()
    return tool.quick_check(text)


def analyze_claim(
    claim: str,
    source_pdf_path: str,
    keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    特定の主張を元論文PDFと照合して分析

    使用例:
    ```python
    from citation_verifier import analyze_claim

    result = analyze_claim(
        claim="この手法は常に99%以上の精度を達成する",
        source_pdf_path="/path/to/paper.pdf",
        keywords=["accuracy", "precision"]
    )
    print(result)
    ```

    Args:
        claim: 検証する主張
        source_pdf_path: 元論文PDFのパス
        keywords: 検索キーワード（省略時は自動抽出）

    Returns:
        分析結果の辞書
    """
    from .pdf_parser import PDFParser

    parser = PDFParser()
    pdf_doc = parser.parse(source_pdf_path)

    verifier = CitationVerifier()
    result = verifier.verify_citation(claim, pdf_doc, keywords)

    return {
        'status': result.status.value,
        'status_label': _get_status_label(result.status),
        'confidence': result.confidence,
        'issues': [
            {
                'type': issue.issue_type.value,
                'description': issue.description,
                'severity': issue.severity,
                'suggestion': issue.suggestion
            }
            for issue in result.issues
        ],
        'source_excerpts': [
            {'page': page, 'text': text[:500]}
            for page, text in result.source_excerpts
        ],
        'recommendations': result.recommendations,
        'analysis': result.analysis
    }


def _get_status_label(status: VerificationStatus) -> str:
    """ステータスの日本語ラベルを取得"""
    labels = {
        VerificationStatus.ACCURATE: "正確",
        VerificationStatus.EXAGGERATED: "誇張あり",
        VerificationStatus.UNDERSTATED: "過小評価",
        VerificationStatus.MISQUOTED: "誤引用",
        VerificationStatus.REVERSED: "逆の結果",
        VerificationStatus.UNSUPPORTED: "根拠なし",
        VerificationStatus.PARTIAL: "部分的に正確",
        VerificationStatus.UNVERIFIABLE: "検証不可",
        VerificationStatus.NO_PDF_MATCH: "PDF未発見",
    }
    return labels.get(status, status.value)


def list_citations(text: str) -> List[Dict[str, Any]]:
    """
    テキストから引用を抽出してリスト化

    Args:
        text: 分析するテキスト

    Returns:
        引用情報のリスト
    """
    parser = CitationParser()
    parsed = parser.parse(text)

    return [
        {
            'raw_text': c.raw_text,
            'authors': c.authors,
            'year': c.year,
            'numbers': c.numbers,
            'claim_text': c.claim_text,
            'style': c.style.value,
            'position': c.position
        }
        for c in parsed.citations
    ]


# 簡単なインタラクティブ使用のためのヘルパー
def help_text() -> str:
    """使用方法のヘルプテキストを返す"""
    return """
# Citation Verification Tool 使用方法

## 基本的な使い方

### 1. 引用を検出する
```python
from citation_verifier import quick_check

text = '''
先行研究では、この手法が有効であることが示されている (Smith, 2020)。
また、Jones et al. (2019) は異なるアプローチを提案した。
'''

print(quick_check(text))
```

### 2. 引用を詳細に検証する
```python
from citation_verifier import verify_citations

result = verify_citations(
    text,
    zotero_path="/path/to/Zotero/storage"
)
print(result)
```

### 3. 特定の主張をPDFと照合する
```python
from citation_verifier import analyze_claim

result = analyze_claim(
    claim="この手法は常に高精度を達成する",
    source_pdf_path="/path/to/paper.pdf"
)
print(result)
```

## 設定

### ローカルZoteroストレージを使用
```python
verify_citations(text, zotero_path="/Users/you/Zotero/storage")
```

### Google Driveを使用（要設定）
```python
from citation_verifier import CitationVerificationTool

tool = CitationVerificationTool(
    use_google_drive=True,
    credentials_path="/path/to/credentials.json",
    zotero_folder_id="YOUR_FOLDER_ID"
)
result = tool.verify_text(text)
```

## 検出される問題

- **誇張 (exaggerated)**: 元論文より強い表現を使用
- **逆の結果 (reversed)**: 結論が元論文と逆
- **誤引用 (misquoted)**: 数値や内容が異なる
- **根拠なし (unsupported)**: 元論文で確認できない
- **部分的 (partial)**: 一部のみ正確
"""
