"""
PDF解析・テキスト抽出モジュール
"""

import io
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Union
from dataclasses import dataclass, field

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from .config import get_config


@dataclass
class PDFMetadata:
    """PDF メタデータ"""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None


@dataclass
class PDFPage:
    """PDF ページ情報"""
    page_number: int
    text: str
    width: float = 0
    height: float = 0


@dataclass
class PDFDocument:
    """解析済みPDFドキュメント"""
    source: str  # ファイルパスまたはID
    metadata: PDFMetadata
    pages: List[PDFPage] = field(default_factory=list)
    full_text: str = ""

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def get_text_around(self, search_text: str, context_chars: int = 500) -> List[Tuple[int, str]]:
        """
        指定テキストの周辺コンテキストを取得

        Args:
            search_text: 検索するテキスト
            context_chars: 前後の文字数

        Returns:
            (ページ番号, 周辺テキスト) のリスト
        """
        results = []
        search_lower = search_text.lower()

        for page in self.pages:
            text_lower = page.text.lower()
            start_pos = 0

            while True:
                pos = text_lower.find(search_lower, start_pos)
                if pos == -1:
                    break

                # 前後のコンテキストを取得
                context_start = max(0, pos - context_chars)
                context_end = min(len(page.text), pos + len(search_text) + context_chars)

                context = page.text[context_start:context_end]
                results.append((page.page_number, context))

                start_pos = pos + 1

        return results

    def search_sentences(self, keywords: List[str], max_results: int = 10) -> List[Tuple[int, str]]:
        """
        キーワードを含む文を検索

        Args:
            keywords: 検索キーワードリスト
            max_results: 最大結果数

        Returns:
            (ページ番号, 文) のリスト
        """
        results = []
        # 文の区切りパターン
        sentence_pattern = re.compile(r'[.!?。！？]\s+|\n\n')

        for page in self.pages:
            sentences = sentence_pattern.split(page.text)
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if all(kw.lower() in sentence_lower for kw in keywords):
                    results.append((page.page_number, sentence.strip()))
                    if len(results) >= max_results:
                        return results

        return results


class PDFParser:
    """PDF解析クラス"""

    def __init__(self, method: Optional[str] = None):
        self.config = get_config()
        self.method = method or self.config.pdf_extraction_method

        if self.method == "pymupdf" and not PYMUPDF_AVAILABLE:
            if PDFPLUMBER_AVAILABLE:
                self.method = "pdfplumber"
            else:
                raise ImportError(
                    "No PDF library available. "
                    "Install PyMuPDF (pip install pymupdf) or "
                    "pdfplumber (pip install pdfplumber)"
                )
        elif self.method == "pdfplumber" and not PDFPLUMBER_AVAILABLE:
            if PYMUPDF_AVAILABLE:
                self.method = "pymupdf"
            else:
                raise ImportError(
                    "No PDF library available. "
                    "Install PyMuPDF (pip install pymupdf) or "
                    "pdfplumber (pip install pdfplumber)"
                )

    def parse(self, source: Union[str, Path, bytes]) -> PDFDocument:
        """
        PDFを解析

        Args:
            source: ファイルパス、またはPDFのバイトデータ

        Returns:
            解析済みPDFDocument
        """
        if self.method == "pymupdf":
            return self._parse_with_pymupdf(source)
        else:
            return self._parse_with_pdfplumber(source)

    def _parse_with_pymupdf(self, source: Union[str, Path, bytes]) -> PDFDocument:
        """PyMuPDFを使用してPDFを解析"""
        if isinstance(source, bytes):
            doc = fitz.open(stream=source, filetype="pdf")
            source_str = "<bytes>"
        else:
            doc = fitz.open(str(source))
            source_str = str(source)

        # メタデータ取得
        meta = doc.metadata or {}
        metadata = PDFMetadata(
            title=meta.get('title'),
            author=meta.get('author'),
            subject=meta.get('subject'),
            keywords=meta.get('keywords'),
            creator=meta.get('creator'),
            producer=meta.get('producer'),
            creation_date=meta.get('creationDate'),
            modification_date=meta.get('modDate')
        )

        # ページごとにテキスト抽出
        pages = []
        full_text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            rect = page.rect

            pages.append(PDFPage(
                page_number=page_num + 1,
                text=text,
                width=rect.width,
                height=rect.height
            ))
            full_text_parts.append(text)

        doc.close()

        return PDFDocument(
            source=source_str,
            metadata=metadata,
            pages=pages,
            full_text="\n\n".join(full_text_parts)
        )

    def _parse_with_pdfplumber(self, source: Union[str, Path, bytes]) -> PDFDocument:
        """pdfplumberを使用してPDFを解析"""
        if isinstance(source, bytes):
            pdf_file = io.BytesIO(source)
            source_str = "<bytes>"
        else:
            pdf_file = str(source)
            source_str = str(source)

        with pdfplumber.open(pdf_file) as pdf:
            # メタデータ取得
            meta = pdf.metadata or {}
            metadata = PDFMetadata(
                title=meta.get('Title'),
                author=meta.get('Author'),
                subject=meta.get('Subject'),
                keywords=meta.get('Keywords'),
                creator=meta.get('Creator'),
                producer=meta.get('Producer'),
                creation_date=meta.get('CreationDate'),
                modification_date=meta.get('ModDate')
            )

            # ページごとにテキスト抽出
            pages = []
            full_text_parts = []

            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                pages.append(PDFPage(
                    page_number=page_num,
                    text=text,
                    width=page.width,
                    height=page.height
                ))
                full_text_parts.append(text)

        return PDFDocument(
            source=source_str,
            metadata=metadata,
            pages=pages,
            full_text="\n\n".join(full_text_parts)
        )


def extract_text_from_pdf(source: Union[str, Path, bytes]) -> str:
    """PDFからテキストを抽出（簡易関数）"""
    parser = PDFParser()
    doc = parser.parse(source)
    return doc.full_text


def extract_metadata_from_pdf(source: Union[str, Path, bytes]) -> PDFMetadata:
    """PDFからメタデータを抽出（簡易関数）"""
    parser = PDFParser()
    doc = parser.parse(source)
    return doc.metadata
