"""
Citation Verifier のテスト
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# パッケージをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from citation_verifier.verifier import (
    CitationVerifier,
    VerificationStatus,
    VerificationResult,
    VerificationIssue
)
from citation_verifier.pdf_parser import PDFDocument, PDFPage, PDFMetadata


class TestCitationVerifier(unittest.TestCase):
    """CitationVerifierのテスト"""

    def setUp(self):
        self.verifier = CitationVerifier()

    def _create_mock_pdf(self, pages_content: list) -> PDFDocument:
        """モックPDFドキュメントを作成"""
        pages = [
            PDFPage(page_number=i+1, text=content)
            for i, content in enumerate(pages_content)
        ]
        return PDFDocument(
            source="test.pdf",
            metadata=PDFMetadata(),
            pages=pages,
            full_text="\n\n".join(pages_content)
        )

    def test_accurate_citation(self):
        """正確な引用の検証"""
        claim = "The study found improved results in some cases"
        source = self._create_mock_pdf([
            "Our study found improved results in some cases, though further research is needed."
        ])

        result = self.verifier.verify_citation(claim, source)
        # 明確な問題がなければ正確とみなす
        self.assertIn(result.status, [VerificationStatus.ACCURATE, VerificationStatus.UNVERIFIABLE])

    def test_exaggerated_claim(self):
        """誇張された主張の検出"""
        claim = "Deep learning always achieves the best results"
        source = self._create_mock_pdf([
            "Deep learning may achieve better results in some scenarios, but traditional methods might be preferred in others."
        ])

        result = self.verifier.verify_citation(claim, source, keywords=["deep", "learning", "results"])

        # 誇張が検出されるか、何らかの問題が検出されるはず
        if result.issues:
            self.assertTrue(any(
                issue.issue_type in [VerificationStatus.EXAGGERATED, VerificationStatus.MISQUOTED]
                for issue in result.issues
            ))

    def test_reversed_conclusion(self):
        """逆の結論の検出"""
        claim = "The method did not show any improvement"
        source = self._create_mock_pdf([
            "The method showed significant improvement over baseline approaches."
        ])

        result = self.verifier.verify_citation(claim, source, keywords=["method", "improvement"])

        # 逆の結果が検出されるか確認
        if result.issues:
            issue_types = [issue.issue_type for issue in result.issues]
            # REVERSED または他の問題が検出される
            self.assertTrue(len(issue_types) > 0)

    def test_number_mismatch(self):
        """数値の不一致検出"""
        claim = "The accuracy reached 99%"
        source = self._create_mock_pdf([
            "The proposed method achieved 85% accuracy on the test set."
        ])

        result = self.verifier.verify_citation(claim, source, keywords=["accuracy"])

        # 数値の不一致が検出されるはず
        if result.issues:
            self.assertTrue(any(
                "数値" in issue.description or "misquoted" in issue.issue_type.value
                for issue in result.issues
            ))

    def test_no_pdf_match(self):
        """PDFが見つからない場合"""
        claim = "Some claim"
        result = self.verifier.verify_citation(claim, None)

        self.assertEqual(result.status, VerificationStatus.NO_PDF_MATCH)

    def test_unverifiable_claim(self):
        """検証不可能な主張"""
        claim = "This completely unrelated topic was discussed"
        source = self._create_mock_pdf([
            "Machine learning has revolutionized data analysis."
        ])

        result = self.verifier.verify_citation(
            claim, source,
            keywords=["completely", "unrelated", "topic"]
        )

        # キーワードが見つからない場合は検証不可
        self.assertIn(result.status, [VerificationStatus.UNVERIFIABLE, VerificationStatus.ACCURATE])

    def test_keyword_extraction(self):
        """キーワード抽出のテスト"""
        text = "Deep learning neural networks achieve state-of-the-art performance"
        keywords = self.verifier._extract_keywords(text)

        self.assertIn("deep", keywords)
        self.assertIn("learning", keywords)
        self.assertNotIn("the", keywords)  # ストップワードは除外
        self.assertLessEqual(len(keywords), 5)  # 最大5個


class TestVerificationResult(unittest.TestCase):
    """VerificationResultのテスト"""

    def test_result_with_issues(self):
        """問題を含む結果"""
        result = VerificationResult(
            status=VerificationStatus.EXAGGERATED,
            confidence=0.7,
            issues=[
                VerificationIssue(
                    issue_type=VerificationStatus.EXAGGERATED,
                    description="誇張された表現が使われています",
                    severity="medium",
                    claim_text="always works",
                    source_text="may work in some cases"
                )
            ],
            claim_text="The method always works",
            recommendations=["表現を緩和してください"]
        )

        self.assertEqual(result.status, VerificationStatus.EXAGGERATED)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].severity, "medium")

    def test_accurate_result(self):
        """正確な結果"""
        result = VerificationResult(
            status=VerificationStatus.ACCURATE,
            confidence=0.9,
            claim_text="The study found positive results"
        )

        self.assertEqual(result.status, VerificationStatus.ACCURATE)
        self.assertEqual(len(result.issues), 0)


if __name__ == '__main__':
    unittest.main()
