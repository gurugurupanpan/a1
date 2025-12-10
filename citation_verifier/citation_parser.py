"""
引用パースモジュール
論文ドラフトから引用を抽出し、構造化する
"""

import re
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class CitationStyle(Enum):
    """引用スタイル"""
    APA = "apa"              # (Author, 2020) or Author (2020)
    MLA = "mla"              # (Author 123) - page number
    VANCOUVER = "vancouver"  # [1], [2], [1-3]
    NUMBERED = "numbered"    # (1), (2), 1), 2)
    FOOTNOTE = "footnote"    # ¹, ², ³ or [^1], [^2]
    UNKNOWN = "unknown"


@dataclass
class Citation:
    """引用情報"""
    raw_text: str           # 元のテキスト
    context: str            # 引用周辺のコンテキスト
    position: Tuple[int, int]  # テキスト内の位置 (start, end)
    style: CitationStyle    # 引用スタイル

    # 抽出された情報（スタイルによって一部のみ）
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    numbers: List[int] = field(default_factory=list)  # 番号引用の場合
    page_numbers: Optional[str] = None

    # クレーム情報
    claim_text: str = ""    # この引用で主張している内容
    claim_type: str = ""    # "supports", "contradicts", "extends", etc.


@dataclass
class ParsedDraft:
    """解析済み論文ドラフト"""
    original_text: str
    citations: List[Citation]
    detected_style: CitationStyle

    def get_citations_by_author(self, author: str) -> List[Citation]:
        """著者名で引用を検索"""
        author_lower = author.lower()
        return [
            c for c in self.citations
            if any(author_lower in a.lower() for a in c.authors)
        ]

    def get_citation_by_number(self, number: int) -> List[Citation]:
        """番号で引用を検索"""
        return [c for c in self.citations if number in c.numbers]


class CitationParser:
    """引用パーサー"""

    # 各スタイルの正規表現パターン
    PATTERNS = {
        # APA: (Author, 2020), (Author & Author, 2020), (Author et al., 2020)
        CitationStyle.APA: [
            # (Author, 2020) or (Author & Author, 2020)
            r'\(([A-Z][a-zA-Z\-]+(?:\s*(?:&|and)\s*[A-Z][a-zA-Z\-]+)*(?:\s*et\s*al\.?)?)\s*,?\s*(\d{4})\)',
            # Author (2020)
            r'([A-Z][a-zA-Z\-]+(?:\s*(?:&|and)\s*[A-Z][a-zA-Z\-]+)*(?:\s*et\s*al\.?)?)\s*\((\d{4})\)',
            # (Author, 2020, p. 123)
            r'\(([A-Z][a-zA-Z\-]+(?:\s*(?:&|and)\s*[A-Z][a-zA-Z\-]+)*(?:\s*et\s*al\.?)?)\s*,?\s*(\d{4})\s*,\s*p+\.\s*[\d\-]+\)',
        ],
        # MLA: (Author 123)
        CitationStyle.MLA: [
            r'\(([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)?)\s+(\d+(?:\-\d+)?)\)',
        ],
        # Vancouver: [1], [2], [1-3], [1,2,3]
        CitationStyle.VANCOUVER: [
            r'\[(\d+(?:\s*[-,]\s*\d+)*)\]',
        ],
        # Numbered: (1), (2), 1), 2)
        CitationStyle.NUMBERED: [
            r'\((\d+(?:\s*,\s*\d+)*)\)',
            r'(?<!\d)(\d+)\)',
        ],
        # Footnote: ¹, ², [^1], [^2]
        CitationStyle.FOOTNOTE: [
            r'\[\^(\d+)\]',
            r'[¹²³⁴⁵⁶⁷⁸⁹⁰]+',
        ],
    }

    def __init__(self, context_chars: int = 200):
        self.context_chars = context_chars

    def parse(self, text: str, style: Optional[CitationStyle] = None) -> ParsedDraft:
        """
        論文ドラフトから引用を抽出

        Args:
            text: 論文ドラフトのテキスト
            style: 引用スタイル（Noneの場合は自動検出）

        Returns:
            ParsedDraft オブジェクト
        """
        if style is None:
            style = self._detect_style(text)

        citations = self._extract_citations(text, style)

        return ParsedDraft(
            original_text=text,
            citations=citations,
            detected_style=style
        )

    def _detect_style(self, text: str) -> CitationStyle:
        """引用スタイルを自動検出"""
        style_counts = {}

        for style, patterns in self.PATTERNS.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, text))
            style_counts[style] = count

        if max(style_counts.values()) == 0:
            return CitationStyle.UNKNOWN

        return max(style_counts, key=style_counts.get)

    def _extract_citations(self, text: str, style: CitationStyle) -> List[Citation]:
        """指定スタイルで引用を抽出"""
        citations = []

        if style == CitationStyle.UNKNOWN:
            # 全スタイルで試行
            for s in CitationStyle:
                if s != CitationStyle.UNKNOWN:
                    citations.extend(self._extract_citations(text, s))
            return citations

        patterns = self.PATTERNS.get(style, [])

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                citation = self._create_citation(text, match, style)
                if citation:
                    citations.append(citation)

        # 重複を除去（位置が近いもの）
        return self._deduplicate_citations(citations)

    def _create_citation(self, text: str, match: re.Match, style: CitationStyle) -> Optional[Citation]:
        """マッチから Citation オブジェクトを作成"""
        start, end = match.span()

        # コンテキストを取得
        context_start = max(0, start - self.context_chars)
        context_end = min(len(text), end + self.context_chars)
        context = text[context_start:context_end]

        # クレームテキストを抽出（引用の前の文）
        claim_text = self._extract_claim(text, start)

        citation = Citation(
            raw_text=match.group(0),
            context=context,
            position=(start, end),
            style=style,
            claim_text=claim_text
        )

        # スタイルに応じて情報を抽出
        if style == CitationStyle.APA:
            groups = match.groups()
            if len(groups) >= 2:
                citation.authors = self._parse_authors(groups[0])
                citation.year = int(groups[1])
            elif len(groups) == 1:
                citation.authors = self._parse_authors(groups[0])

        elif style == CitationStyle.MLA:
            groups = match.groups()
            if len(groups) >= 2:
                citation.authors = self._parse_authors(groups[0])
                citation.page_numbers = groups[1]

        elif style in (CitationStyle.VANCOUVER, CitationStyle.NUMBERED):
            groups = match.groups()
            if groups:
                citation.numbers = self._parse_numbers(groups[0])

        elif style == CitationStyle.FOOTNOTE:
            groups = match.groups()
            if groups:
                citation.numbers = self._parse_numbers(groups[0])

        return citation

    def _parse_authors(self, author_str: str) -> List[str]:
        """著者文字列をパース"""
        # "et al." を除去
        author_str = re.sub(r'\s*et\s*al\.?', '', author_str)

        # "&" や "and" で分割
        authors = re.split(r'\s*(?:&|and)\s*', author_str)
        return [a.strip() for a in authors if a.strip()]

    def _parse_numbers(self, num_str: str) -> List[int]:
        """番号文字列をパース（例: "1-3,5" -> [1,2,3,5]）"""
        numbers = []
        parts = re.split(r'\s*,\s*', num_str)

        for part in parts:
            if '-' in part:
                try:
                    start, end = part.split('-')
                    numbers.extend(range(int(start), int(end) + 1))
                except ValueError:
                    pass
            else:
                try:
                    numbers.append(int(part))
                except ValueError:
                    pass

        return sorted(set(numbers))

    def _extract_claim(self, text: str, citation_pos: int) -> str:
        """引用の前の文（クレーム）を抽出"""
        # 引用位置より前のテキストを取得
        before_text = text[:citation_pos]

        # 最後の文を取得
        sentences = re.split(r'[.!?。！？]\s+', before_text)
        if sentences:
            return sentences[-1].strip()
        return ""

    def _deduplicate_citations(self, citations: List[Citation]) -> List[Citation]:
        """重複する引用を除去"""
        if not citations:
            return citations

        # 位置でソート
        citations.sort(key=lambda c: c.position[0])

        deduplicated = [citations[0]]
        for citation in citations[1:]:
            last = deduplicated[-1]
            # 位置が重なる場合はスキップ
            if citation.position[0] < last.position[1]:
                continue
            deduplicated.append(citation)

        return deduplicated


def extract_citations(text: str, style: Optional[CitationStyle] = None) -> List[Citation]:
    """引用を抽出（簡易関数）"""
    parser = CitationParser()
    parsed = parser.parse(text, style)
    return parsed.citations


def detect_citation_style(text: str) -> CitationStyle:
    """引用スタイルを検出（簡易関数）"""
    parser = CitationParser()
    return parser._detect_style(text)
