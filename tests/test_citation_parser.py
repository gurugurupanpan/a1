"""
Citation Parser のテスト
"""

import unittest
import sys
from pathlib import Path

# パッケージをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from citation_verifier.citation_parser import (
    CitationParser,
    CitationStyle,
    extract_citations,
    detect_citation_style
)


class TestCitationParser(unittest.TestCase):
    """CitationParserのテスト"""

    def setUp(self):
        self.parser = CitationParser()

    def test_detect_apa_style(self):
        """APAスタイルの検出"""
        # APAスタイルを明確に検出できるテキスト（カンマ付き形式）
        text = "This was shown (Smith, 2020) and confirmed (Jones, 2019)."
        style = detect_citation_style(text)
        self.assertEqual(style, CitationStyle.APA)

    def test_detect_vancouver_style(self):
        """Vancouverスタイルの検出"""
        text = "Previous studies [1] have shown that [2-4] this is true."
        style = detect_citation_style(text)
        self.assertEqual(style, CitationStyle.VANCOUVER)

    def test_extract_apa_citations(self):
        """APA形式の引用抽出"""
        text = "Research shows (Smith, 2020) that deep learning is effective (Jones & Brown, 2019)."
        citations = extract_citations(text, CitationStyle.APA)

        self.assertEqual(len(citations), 2)
        self.assertEqual(citations[0].authors, ['Smith'])
        self.assertEqual(citations[0].year, 2020)
        self.assertIn('Jones', citations[1].authors)
        self.assertEqual(citations[1].year, 2019)

    def test_extract_vancouver_citations(self):
        """Vancouver形式の引用抽出"""
        text = "Studies [1] and [2-4] show this effect."
        citations = extract_citations(text, CitationStyle.VANCOUVER)

        self.assertEqual(len(citations), 2)
        self.assertEqual(citations[0].numbers, [1])
        self.assertEqual(citations[1].numbers, [2, 3, 4])

    def test_extract_author_et_al(self):
        """et al.を含む引用の抽出"""
        text = "According to Smith et al. (2020), this is significant."
        citations = extract_citations(text, CitationStyle.APA)

        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0].authors, ['Smith'])
        self.assertEqual(citations[0].year, 2020)

    def test_claim_text_extraction(self):
        """クレームテキストの抽出"""
        text = "Deep learning always outperforms traditional methods (Smith, 2020)."
        citations = extract_citations(text, CitationStyle.APA)

        self.assertEqual(len(citations), 1)
        self.assertIn("Deep learning", citations[0].claim_text)

    def test_multiple_authors(self):
        """複数著者の引用"""
        text = "Research by Smith and Jones (2020) and Brown & White (2019)."
        citations = extract_citations(text, CitationStyle.APA)

        self.assertGreaterEqual(len(citations), 1)

    def test_empty_text(self):
        """空テキスト"""
        citations = extract_citations("")
        self.assertEqual(len(citations), 0)

    def test_no_citations(self):
        """引用のないテキスト"""
        text = "This is a normal sentence without any citations."
        citations = extract_citations(text)
        self.assertEqual(len(citations), 0)


class TestParsedDraft(unittest.TestCase):
    """ParsedDraftのテスト"""

    def setUp(self):
        self.parser = CitationParser()

    def test_get_citations_by_author(self):
        """著者名で引用を検索"""
        # 明確なAPA形式（カンマ付き）を使用
        text = """
        Research shows (Smith, 2020) and (Jones, 2019). Later (Smith & Brown, 2021) extended this.
        """
        parsed = self.parser.parse(text, CitationStyle.APA)

        smith_citations = parsed.get_citations_by_author("Smith")
        self.assertGreaterEqual(len(smith_citations), 1)

    def test_get_citation_by_number(self):
        """番号で引用を検索"""
        text = "Studies [1] and [2] and [3-5] show this."
        parsed = self.parser.parse(text, CitationStyle.VANCOUVER)

        citation = parsed.get_citation_by_number(3)
        self.assertEqual(len(citation), 1)
        self.assertIn(3, citation[0].numbers)


if __name__ == '__main__':
    unittest.main()
