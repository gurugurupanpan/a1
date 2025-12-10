"""
Citation Verification Tool
論文ドラフトの引用を元論文PDFと照合し、誤引用・誇張・逆の結果を検出するツール
"""

__version__ = "0.1.0"

# 主要なAPIをエクスポート
from .api import (
    verify_citations,
    quick_check,
    analyze_claim,
    list_citations,
    help_text,
)

from .main import CitationVerificationTool

from .verifier import (
    VerificationStatus,
    VerificationResult,
    VerificationIssue,
)

from .citation_parser import (
    Citation,
    CitationStyle,
    CitationParser,
    extract_citations,
    detect_citation_style,
)

from .pdf_parser import (
    PDFDocument,
    PDFParser,
    extract_text_from_pdf,
)

from .config import Config, get_config

__all__ = [
    # 主要API
    'verify_citations',
    'quick_check',
    'analyze_claim',
    'list_citations',
    'help_text',

    # メインツール
    'CitationVerificationTool',

    # 検証関連
    'VerificationStatus',
    'VerificationResult',
    'VerificationIssue',

    # 引用パース
    'Citation',
    'CitationStyle',
    'CitationParser',
    'extract_citations',
    'detect_citation_style',

    # PDF解析
    'PDFDocument',
    'PDFParser',
    'extract_text_from_pdf',

    # 設定
    'Config',
    'get_config',
]
