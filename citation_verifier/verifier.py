"""
引用検証モジュール
誤引用・誇張・逆の結果を検出する
"""

import re
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum


class VerificationStatus(Enum):
    """検証ステータス"""
    ACCURATE = "accurate"           # 正確な引用
    EXAGGERATED = "exaggerated"     # 誇張あり
    UNDERSTATED = "understated"     # 過小評価
    MISQUOTED = "misquoted"         # 誤引用（内容が異なる）
    REVERSED = "reversed"           # 逆の結果
    UNSUPPORTED = "unsupported"     # 元論文でサポートされていない
    PARTIAL = "partial"             # 部分的に正確
    UNVERIFIABLE = "unverifiable"   # 検証不可能
    NO_PDF_MATCH = "no_pdf_match"   # PDFが見つからない


@dataclass
class VerificationIssue:
    """検証で見つかった問題"""
    issue_type: VerificationStatus
    description: str
    severity: str  # "low", "medium", "high", "critical"
    claim_text: str
    source_text: str
    suggestion: str = ""


@dataclass
class VerificationResult:
    """検証結果"""
    status: VerificationStatus
    confidence: float  # 0.0 - 1.0
    issues: List[VerificationIssue] = field(default_factory=list)

    # 引用の主張
    claim_text: str = ""

    # 元論文からの関連テキスト
    source_excerpts: List[Tuple[int, str]] = field(default_factory=list)

    # 詳細な分析
    analysis: str = ""

    # 推奨アクション
    recommendations: List[str] = field(default_factory=list)


class CitationVerifier:
    """引用検証クラス"""

    # 誇張を示唆するパターン
    EXAGGERATION_PATTERNS = [
        (r'\b(always|never|all|none|every|no one)\b', 'absolute_claim'),
        (r'\b(prove[sd]?|definitive|conclusive)\b', 'certainty_claim'),
        (r'\b(significantly?|dramatically|greatly|substantially)\b', 'magnitude_claim'),
        (r'\b(revolutionary|breakthrough|groundbreaking)\b', 'novelty_claim'),
    ]

    # ヘッジング（慎重な表現）パターン
    HEDGING_PATTERNS = [
        r'\b(may|might|could|possibly|potentially)\b',
        r'\b(suggest[s]?|indicate[s]?|appear[s]?)\b',
        r'\b(some|several|few|limited)\b',
        r'\b(tend[s]? to|seem[s]? to)\b',
    ]

    # 否定パターン
    NEGATION_PATTERNS = [
        r'\b(not|no|never|neither|nor)\b',
        r'\b(fail(ed)?|unable|cannot|could not)\b',
        r'\b(reject(ed)?|refute[sd]?|contradict[s]?)\b',
        r'\b(insignificant|negligible|marginal)\b',
    ]

    def __init__(self, context_window: int = 500):
        self.context_window = context_window

    def verify_citation(
        self,
        claim_text: str,
        source_document,  # PDFDocument
        keywords: Optional[List[str]] = None
    ) -> VerificationResult:
        """
        引用を検証

        Args:
            claim_text: 論文ドラフト内の主張
            source_document: 元論文のPDFDocument
            keywords: 検索キーワード（Noneの場合は自動抽出）

        Returns:
            VerificationResult
        """
        result = VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            confidence=0.0,
            claim_text=claim_text
        )

        if source_document is None:
            result.status = VerificationStatus.NO_PDF_MATCH
            result.analysis = "元論文のPDFが見つかりませんでした。"
            return result

        # キーワードを抽出
        if keywords is None:
            keywords = self._extract_keywords(claim_text)

        # 元論文から関連テキストを検索
        source_excerpts = source_document.search_sentences(keywords, max_results=10)

        if not source_excerpts:
            # キーワードを減らして再検索
            if len(keywords) > 1:
                for i in range(len(keywords) - 1, 0, -1):
                    source_excerpts = source_document.search_sentences(
                        keywords[:i], max_results=10
                    )
                    if source_excerpts:
                        break

        result.source_excerpts = source_excerpts

        if not source_excerpts:
            result.status = VerificationStatus.UNVERIFIABLE
            result.analysis = (
                f"元論文内でキーワード {keywords} に関連するテキストが見つかりませんでした。"
            )
            result.recommendations.append(
                "引用が正しい論文を参照しているか確認してください。"
            )
            return result

        # 検証を実行
        issues = []

        # 1. 誇張チェック
        exaggeration_issues = self._check_exaggeration(claim_text, source_excerpts)
        issues.extend(exaggeration_issues)

        # 2. 逆の結果チェック
        reversal_issues = self._check_reversal(claim_text, source_excerpts)
        issues.extend(reversal_issues)

        # 3. 根拠の有無チェック
        support_issues = self._check_support(claim_text, source_excerpts)
        issues.extend(support_issues)

        result.issues = issues

        # 総合的なステータスを決定
        result.status, result.confidence = self._determine_status(issues)

        # 分析テキストを生成
        result.analysis = self._generate_analysis(claim_text, source_excerpts, issues)

        # 推奨アクションを生成
        result.recommendations = self._generate_recommendations(issues)

        return result

    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        # ストップワードを除去
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'that', 'this', 'these', 'those', 'and', 'but', 'or',
            'nor', 'so', 'yet', 'both', 'either', 'neither', 'not',
            'only', 'own', 'same', 'than', 'too', 'very', 'just',
        }

        # 単語を抽出
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # ストップワードを除去し、ユニークな単語を取得
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and word not in seen:
                keywords.append(word)
                seen.add(word)

        return keywords[:5]  # 最大5個

    def _check_exaggeration(
        self,
        claim_text: str,
        source_excerpts: List[Tuple[int, str]]
    ) -> List[VerificationIssue]:
        """誇張をチェック"""
        issues = []
        claim_lower = claim_text.lower()

        # 主張内の誇張パターンを検出
        for pattern, pattern_type in self.EXAGGERATION_PATTERNS:
            if re.search(pattern, claim_lower, re.IGNORECASE):
                # 元論文でも同様の表現があるかチェック
                found_in_source = False
                for _, excerpt in source_excerpts:
                    if re.search(pattern, excerpt.lower(), re.IGNORECASE):
                        found_in_source = True
                        break

                if not found_in_source:
                    # 元論文にヘッジングがあるかチェック
                    has_hedging = False
                    for _, excerpt in source_excerpts:
                        for hedge_pattern in self.HEDGING_PATTERNS:
                            if re.search(hedge_pattern, excerpt.lower(), re.IGNORECASE):
                                has_hedging = True
                                break
                        if has_hedging:
                            break

                    if has_hedging:
                        issues.append(VerificationIssue(
                            issue_type=VerificationStatus.EXAGGERATED,
                            description=f"主張で絶対的な表現が使われていますが、"
                                       f"元論文では慎重な表現（may, might等）が使われています。",
                            severity="medium",
                            claim_text=claim_text,
                            source_text=source_excerpts[0][1] if source_excerpts else "",
                            suggestion="元論文の慎重な表現に合わせて修正することを検討してください。"
                        ))

        return issues

    def _check_reversal(
        self,
        claim_text: str,
        source_excerpts: List[Tuple[int, str]]
    ) -> List[VerificationIssue]:
        """逆の結果をチェック"""
        issues = []
        claim_lower = claim_text.lower()

        # 主張に否定があるかチェック
        claim_has_negation = any(
            re.search(pattern, claim_lower, re.IGNORECASE)
            for pattern in self.NEGATION_PATTERNS
        )

        # 元論文の否定をチェック
        source_has_negation = False
        negation_excerpt = ""
        for _, excerpt in source_excerpts:
            excerpt_lower = excerpt.lower()
            for pattern in self.NEGATION_PATTERNS:
                if re.search(pattern, excerpt_lower, re.IGNORECASE):
                    source_has_negation = True
                    negation_excerpt = excerpt
                    break
            if source_has_negation:
                break

        # 主張と元論文で否定の有無が異なる場合
        if claim_has_negation != source_has_negation:
            issues.append(VerificationIssue(
                issue_type=VerificationStatus.REVERSED,
                description="主張と元論文で結果の方向性が異なる可能性があります。",
                severity="critical",
                claim_text=claim_text,
                source_text=negation_excerpt or (source_excerpts[0][1] if source_excerpts else ""),
                suggestion="元論文の結論を再確認し、引用内容を修正してください。"
            ))

        return issues

    def _check_support(
        self,
        claim_text: str,
        source_excerpts: List[Tuple[int, str]]
    ) -> List[VerificationIssue]:
        """根拠の有無をチェック"""
        issues = []

        # 数値の比較
        claim_numbers = re.findall(r'\d+(?:\.\d+)?%?', claim_text)
        source_numbers = []
        for _, excerpt in source_excerpts:
            source_numbers.extend(re.findall(r'\d+(?:\.\d+)?%?', excerpt))

        # 主張に数値があるが元論文にない場合
        if claim_numbers and not source_numbers:
            issues.append(VerificationIssue(
                issue_type=VerificationStatus.UNSUPPORTED,
                description=f"主張に数値({', '.join(claim_numbers)})がありますが、"
                           f"元論文の該当箇所では確認できませんでした。",
                severity="high",
                claim_text=claim_text,
                source_text=source_excerpts[0][1] if source_excerpts else "",
                suggestion="数値の出典を確認してください。"
            ))

        # 主張の数値と元論文の数値が異なる場合
        if claim_numbers and source_numbers:
            claim_set = set(claim_numbers)
            source_set = set(source_numbers)
            if not claim_set.intersection(source_set):
                issues.append(VerificationIssue(
                    issue_type=VerificationStatus.MISQUOTED,
                    description=f"主張の数値({', '.join(claim_numbers)})と"
                               f"元論文の数値({', '.join(source_numbers[:3])})が異なります。",
                    severity="high",
                    claim_text=claim_text,
                    source_text=source_excerpts[0][1] if source_excerpts else "",
                    suggestion="正確な数値を元論文から確認してください。"
                ))

        return issues

    def _determine_status(
        self,
        issues: List[VerificationIssue]
    ) -> Tuple[VerificationStatus, float]:
        """問題リストから総合的なステータスを決定"""
        if not issues:
            return VerificationStatus.ACCURATE, 0.8

        # 最も深刻な問題を基準にする
        severity_order = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }

        max_severity = max(severity_order.get(i.severity, 0) for i in issues)

        # ステータス優先順位
        status_priority = {
            VerificationStatus.REVERSED: 5,
            VerificationStatus.MISQUOTED: 4,
            VerificationStatus.UNSUPPORTED: 3,
            VerificationStatus.EXAGGERATED: 2,
            VerificationStatus.UNDERSTATED: 1,
            VerificationStatus.PARTIAL: 0,
        }

        issue_types = [i.issue_type for i in issues]
        primary_status = max(issue_types, key=lambda s: status_priority.get(s, -1))

        # 信頼度を計算
        confidence = 0.9 - (len(issues) * 0.1) - (max_severity * 0.1)
        confidence = max(0.3, min(0.9, confidence))

        return primary_status, confidence

    def _generate_analysis(
        self,
        claim_text: str,
        source_excerpts: List[Tuple[int, str]],
        issues: List[VerificationIssue]
    ) -> str:
        """分析テキストを生成"""
        analysis_parts = []

        analysis_parts.append("## 検証分析\n")

        analysis_parts.append("### 主張\n")
        analysis_parts.append(f"> {claim_text}\n")

        analysis_parts.append("### 元論文からの関連テキスト\n")
        for page_num, excerpt in source_excerpts[:3]:
            excerpt_clean = excerpt.replace('\n', ' ')[:300]
            analysis_parts.append(f"- (p.{page_num}) {excerpt_clean}...\n")

        if issues:
            analysis_parts.append("### 検出された問題\n")
            for issue in issues:
                analysis_parts.append(f"- **{issue.issue_type.value}** [{issue.severity}]: {issue.description}\n")

        return "\n".join(analysis_parts)

    def _generate_recommendations(
        self,
        issues: List[VerificationIssue]
    ) -> List[str]:
        """推奨アクションを生成"""
        recommendations = []

        for issue in issues:
            if issue.suggestion:
                recommendations.append(issue.suggestion)

        if not recommendations:
            recommendations.append("引用内容は概ね正確と思われますが、"
                                  "最終確認をお勧めします。")

        return list(set(recommendations))  # 重複を除去
