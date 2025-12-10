"""
引用とPDFのマッチングモジュール
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Union
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .citation_parser import Citation, CitationStyle
from .pdf_parser import PDFDocument, PDFParser, PDFMetadata
from .google_drive import GoogleDriveClient, LocalZoteroStorage, DriveFile


@dataclass
class MatchResult:
    """マッチング結果"""
    citation: Citation
    matched_pdf: Optional[Union[DriveFile, Path]] = None
    pdf_document: Optional[PDFDocument] = None
    confidence: float = 0.0
    match_method: str = ""  # "author_year", "title", "filename", etc.
    candidates: List[Tuple[Union[DriveFile, Path], float]] = field(default_factory=list)


class PDFMatcher:
    """引用とPDFをマッチングするクラス"""

    def __init__(
        self,
        use_google_drive: bool = False,
        local_path: Optional[str] = None,
        credentials_path: Optional[str] = None,
        zotero_folder_id: Optional[str] = None
    ):
        self.use_google_drive = use_google_drive
        self.pdf_parser = PDFParser()

        if use_google_drive:
            self.drive_client = GoogleDriveClient(credentials_path)
            self.zotero_folder_id = zotero_folder_id
            self.local_storage = None
        else:
            self.drive_client = None
            self.local_storage = LocalZoteroStorage(local_path)

        # PDFのキャッシュ
        self._pdf_list_cache: Optional[List] = None
        self._pdf_content_cache: Dict[str, PDFDocument] = {}

    def get_pdf_list(self) -> List[Union[DriveFile, Path]]:
        """利用可能なPDFの一覧を取得"""
        if self._pdf_list_cache is not None:
            return self._pdf_list_cache

        if self.use_google_drive:
            self._pdf_list_cache = self.drive_client.list_pdfs_in_folder(
                self.zotero_folder_id
            )
        else:
            self._pdf_list_cache = self.local_storage.list_pdfs()

        return self._pdf_list_cache

    def get_pdf_content(self, pdf: Union[DriveFile, Path]) -> PDFDocument:
        """PDFの内容を取得（キャッシュあり）"""
        cache_key = pdf.id if isinstance(pdf, DriveFile) else str(pdf)

        if cache_key in self._pdf_content_cache:
            return self._pdf_content_cache[cache_key]

        if isinstance(pdf, DriveFile):
            pdf_bytes = self.drive_client.download_pdf(pdf.id)
            doc = self.pdf_parser.parse(pdf_bytes)
        else:
            doc = self.pdf_parser.parse(pdf)

        self._pdf_content_cache[cache_key] = doc
        return doc

    def match_citation(self, citation: Citation) -> MatchResult:
        """
        引用に対応するPDFを検索

        Args:
            citation: 引用情報

        Returns:
            マッチング結果
        """
        pdf_list = self.get_pdf_list()
        candidates = []

        for pdf in pdf_list:
            score, method = self._calculate_match_score(citation, pdf)
            if score > 0:
                candidates.append((pdf, score, method))

        # スコアでソート
        candidates.sort(key=lambda x: x[1], reverse=True)

        result = MatchResult(
            citation=citation,
            candidates=[(c[0], c[1]) for c in candidates[:5]]  # 上位5件
        )

        if candidates and candidates[0][1] >= 0.5:
            best_match = candidates[0]
            result.matched_pdf = best_match[0]
            result.confidence = best_match[1]
            result.match_method = best_match[2]

            # PDFの内容を取得
            try:
                result.pdf_document = self.get_pdf_content(best_match[0])
            except Exception as e:
                print(f"Warning: Could not load PDF content: {e}")

        return result

    def match_all_citations(self, citations: List[Citation]) -> List[MatchResult]:
        """複数の引用をマッチング"""
        return [self.match_citation(c) for c in citations]

    def _calculate_match_score(
        self,
        citation: Citation,
        pdf: Union[DriveFile, Path]
    ) -> Tuple[float, str]:
        """引用とPDFのマッチングスコアを計算"""
        pdf_name = pdf.name if isinstance(pdf, DriveFile) else pdf.name
        pdf_name_lower = pdf_name.lower()

        best_score = 0.0
        best_method = ""

        # 方法1: 著者名 + 年でマッチング
        if citation.authors and citation.year:
            author_year_score = self._author_year_match(
                citation.authors, citation.year, pdf_name_lower
            )
            if author_year_score > best_score:
                best_score = author_year_score
                best_method = "author_year"

        # 方法2: 著者名のみでマッチング
        if citation.authors:
            author_score = self._author_match(citation.authors, pdf_name_lower)
            if author_score > best_score:
                best_score = author_score
                best_method = "author"

        # 方法3: ファイル名の類似度
        if citation.raw_text:
            similarity_score = self._filename_similarity(citation.raw_text, pdf_name)
            if similarity_score > best_score:
                best_score = similarity_score
                best_method = "filename_similarity"

        return best_score, best_method

    def _author_year_match(
        self,
        authors: List[str],
        year: int,
        pdf_name: str
    ) -> float:
        """著者名 + 年でマッチング"""
        year_str = str(year)
        year_found = year_str in pdf_name

        if not year_found:
            return 0.0

        # 著者名のマッチングスコア
        author_scores = []
        for author in authors:
            author_lower = author.lower()
            if author_lower in pdf_name:
                author_scores.append(1.0)
            else:
                # 部分一致
                for part in author_lower.split():
                    if len(part) > 2 and part in pdf_name:
                        author_scores.append(0.7)
                        break

        if not author_scores:
            return 0.0

        # 著者スコアの平均 × 0.8 + 年マッチ 0.2
        return (sum(author_scores) / len(author_scores)) * 0.8 + 0.2

    def _author_match(self, authors: List[str], pdf_name: str) -> float:
        """著者名のみでマッチング"""
        author_scores = []

        for author in authors:
            author_lower = author.lower()
            if author_lower in pdf_name:
                author_scores.append(1.0)
            else:
                # 部分一致
                for part in author_lower.split():
                    if len(part) > 2 and part in pdf_name:
                        author_scores.append(0.5)
                        break

        if not author_scores:
            return 0.0

        return (sum(author_scores) / len(author_scores)) * 0.6

    def _filename_similarity(self, citation_text: str, pdf_name: str) -> float:
        """ファイル名との類似度を計算"""
        # 括弧や特殊文字を除去
        clean_citation = re.sub(r'[^\w\s]', '', citation_text.lower())
        clean_pdf = re.sub(r'[^\w\s]', '', pdf_name.lower())

        # SequenceMatcherで類似度を計算
        ratio = SequenceMatcher(None, clean_citation, clean_pdf).ratio()
        return ratio * 0.5  # 他の方法より低く評価


class ReferenceListMatcher:
    """
    参考文献リストを使用したマッチング
    番号付き引用（[1], [2]など）を参考文献リストと紐付ける
    """

    def __init__(self):
        self.reference_list: Dict[int, Dict] = {}

    def parse_reference_list(self, reference_text: str) -> Dict[int, Dict]:
        """
        参考文献リストをパース

        Args:
            reference_text: 参考文献リストのテキスト

        Returns:
            {番号: {authors, title, year, ...}} の辞書
        """
        references = {}

        # 番号付きリストのパターン
        patterns = [
            # [1] Author. Title. Year.
            r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|$)',
            # 1. Author. Title. Year.
            r'^(\d+)\.\s*(.+?)(?=^\d+\.|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, reference_text, re.MULTILINE | re.DOTALL)
            if matches:
                for num_str, content in matches:
                    num = int(num_str)
                    ref_info = self._parse_reference_entry(content)
                    references[num] = ref_info
                break

        self.reference_list = references
        return references

    def _parse_reference_entry(self, entry: str) -> Dict:
        """個別の参考文献エントリをパース"""
        entry = entry.strip()

        result = {
            'raw': entry,
            'authors': [],
            'title': None,
            'year': None,
        }

        # 年を抽出
        year_match = re.search(r'\((\d{4})\)|(\d{4})\.', entry)
        if year_match:
            result['year'] = int(year_match.group(1) or year_match.group(2))

        # 著者を抽出（最初のピリオドまで）
        author_match = re.match(r'^([^.]+)\.', entry)
        if author_match:
            author_text = author_match.group(1)
            # カンマや & で分割
            authors = re.split(r',\s*(?:&\s*)?|,?\s*&\s*', author_text)
            result['authors'] = [a.strip() for a in authors if a.strip()]

        # タイトルを抽出
        title_match = re.search(r'\.([^.]+)\.', entry)
        if title_match:
            result['title'] = title_match.group(1).strip()

        return result

    def get_reference_for_citation(self, citation: Citation) -> Optional[Dict]:
        """引用番号から参考文献情報を取得"""
        if not citation.numbers:
            return None

        # 最初の番号で検索
        num = citation.numbers[0]
        return self.reference_list.get(num)
