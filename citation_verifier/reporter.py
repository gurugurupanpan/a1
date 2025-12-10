"""
レポート生成モジュール
検証結果をわかりやすく整形する
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import asdict
from datetime import datetime

from .citation_parser import Citation, ParsedDraft
from .matcher import MatchResult
from .verifier import VerificationResult, VerificationStatus


class VerificationReport:
    """検証レポート"""

    def __init__(
        self,
        draft_text: str,
        parsed_draft: ParsedDraft,
        match_results: List[MatchResult],
        verification_results: List[VerificationResult]
    ):
        self.draft_text = draft_text
        self.parsed_draft = parsed_draft
        self.match_results = match_results
        self.verification_results = verification_results
        self.timestamp = datetime.now()

    @property
    def total_citations(self) -> int:
        return len(self.parsed_draft.citations)

    @property
    def matched_citations(self) -> int:
        return sum(1 for m in self.match_results if m.matched_pdf is not None)

    @property
    def issues_found(self) -> int:
        return sum(len(v.issues) for v in self.verification_results)

    @property
    def critical_issues(self) -> int:
        count = 0
        for v in self.verification_results:
            count += sum(1 for i in v.issues if i.severity == 'critical')
        return count

    def get_summary_stats(self) -> Dict[str, Any]:
        """サマリー統計を取得"""
        status_counts = {}
        for v in self.verification_results:
            status = v.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            'total_citations': self.total_citations,
            'matched_citations': self.matched_citations,
            'unmatched_citations': self.total_citations - self.matched_citations,
            'issues_found': self.issues_found,
            'critical_issues': self.critical_issues,
            'status_distribution': status_counts
        }


class ReportGenerator:
    """レポート生成クラス"""

    # ステータス別の絵文字（Markdownレポート用）
    STATUS_ICONS = {
        VerificationStatus.ACCURATE: "✅",
        VerificationStatus.EXAGGERATED: "⚠️",
        VerificationStatus.UNDERSTATED: "📉",
        VerificationStatus.MISQUOTED: "❌",
        VerificationStatus.REVERSED: "🔄",
        VerificationStatus.UNSUPPORTED: "❓",
        VerificationStatus.PARTIAL: "🔶",
        VerificationStatus.UNVERIFIABLE: "🔍",
        VerificationStatus.NO_PDF_MATCH: "📄",
    }

    # ステータス別の日本語ラベル
    STATUS_LABELS_JA = {
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

    def generate_markdown(self, report: VerificationReport) -> str:
        """Markdownレポートを生成"""
        lines = []

        # ヘッダー
        lines.append("# 引用検証レポート")
        lines.append(f"\n生成日時: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # サマリー
        stats = report.get_summary_stats()
        lines.append("## 概要")
        lines.append("")
        lines.append(f"- **検出された引用数**: {stats['total_citations']}")
        lines.append(f"- **PDF照合成功**: {stats['matched_citations']}")
        lines.append(f"- **PDF照合失敗**: {stats['unmatched_citations']}")
        lines.append(f"- **問題検出数**: {stats['issues_found']}")
        lines.append(f"- **重大な問題**: {stats['critical_issues']}")
        lines.append("")

        # ステータス分布
        lines.append("### ステータス分布")
        lines.append("")
        for status_value, count in stats['status_distribution'].items():
            try:
                status = VerificationStatus(status_value)
                icon = self.STATUS_ICONS.get(status, "")
                label = self.STATUS_LABELS_JA.get(status, status_value)
                lines.append(f"- {icon} {label}: {count}")
            except ValueError:
                lines.append(f"- {status_value}: {count}")
        lines.append("")

        # 各引用の詳細
        lines.append("## 引用別詳細")
        lines.append("")

        for i, (citation, match, verification) in enumerate(zip(
            report.parsed_draft.citations,
            report.match_results,
            report.verification_results
        ), 1):
            icon = self.STATUS_ICONS.get(verification.status, "")
            label = self.STATUS_LABELS_JA.get(verification.status, verification.status.value)

            lines.append(f"### 引用 {i}: {citation.raw_text}")
            lines.append("")
            lines.append(f"**ステータス**: {icon} {label} (信頼度: {verification.confidence:.0%})")
            lines.append("")

            # 主張テキスト
            if citation.claim_text:
                lines.append("**主張**:")
                lines.append(f"> {citation.claim_text}")
                lines.append("")

            # PDFマッチング情報
            if match.matched_pdf:
                pdf_name = match.matched_pdf.name if hasattr(match.matched_pdf, 'name') else match.matched_pdf.name
                lines.append(f"**照合PDF**: {pdf_name} (信頼度: {match.confidence:.0%})")
            else:
                lines.append("**照合PDF**: ❌ 見つかりませんでした")
            lines.append("")

            # 元論文からの抜粋
            if verification.source_excerpts:
                lines.append("**元論文からの関連テキスト**:")
                for page_num, excerpt in verification.source_excerpts[:2]:
                    excerpt_clean = excerpt.replace('\n', ' ')[:200]
                    lines.append(f"> (p.{page_num}) {excerpt_clean}...")
                lines.append("")

            # 問題点
            if verification.issues:
                lines.append("**検出された問題**:")
                for issue in verification.issues:
                    severity_badge = {
                        'critical': '🔴',
                        'high': '🟠',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(issue.severity, '')
                    lines.append(f"- {severity_badge} **{issue.issue_type.value}**: {issue.description}")
                lines.append("")

            # 推奨アクション
            if verification.recommendations:
                lines.append("**推奨アクション**:")
                for rec in verification.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def generate_json(self, report: VerificationReport) -> str:
        """JSONレポートを生成"""
        data = {
            'timestamp': report.timestamp.isoformat(),
            'summary': report.get_summary_stats(),
            'citations': []
        }

        for citation, match, verification in zip(
            report.parsed_draft.citations,
            report.match_results,
            report.verification_results
        ):
            citation_data = {
                'raw_text': citation.raw_text,
                'claim_text': citation.claim_text,
                'authors': citation.authors,
                'year': citation.year,
                'position': citation.position,
                'matched_pdf': None,
                'match_confidence': match.confidence,
                'verification_status': verification.status.value,
                'verification_confidence': verification.confidence,
                'issues': [],
                'source_excerpts': [],
                'recommendations': verification.recommendations
            }

            if match.matched_pdf:
                if hasattr(match.matched_pdf, 'name'):
                    citation_data['matched_pdf'] = match.matched_pdf.name
                else:
                    citation_data['matched_pdf'] = str(match.matched_pdf.name)

            for issue in verification.issues:
                citation_data['issues'].append({
                    'type': issue.issue_type.value,
                    'description': issue.description,
                    'severity': issue.severity,
                    'suggestion': issue.suggestion
                })

            for page_num, excerpt in verification.source_excerpts:
                citation_data['source_excerpts'].append({
                    'page': page_num,
                    'text': excerpt[:500]
                })

            data['citations'].append(citation_data)

        return json.dumps(data, ensure_ascii=False, indent=2)

    def generate_console(self, report: VerificationReport) -> str:
        """コンソール出力用レポートを生成"""
        lines = []

        # ヘッダー
        lines.append("=" * 60)
        lines.append("         引用検証レポート")
        lines.append("=" * 60)
        lines.append("")

        # サマリー
        stats = report.get_summary_stats()
        lines.append(f"引用数: {stats['total_citations']}  "
                    f"照合成功: {stats['matched_citations']}  "
                    f"問題: {stats['issues_found']}  "
                    f"重大: {stats['critical_issues']}")
        lines.append("")
        lines.append("-" * 60)

        # 問題のある引用のみ詳細表示
        for i, (citation, match, verification) in enumerate(zip(
            report.parsed_draft.citations,
            report.match_results,
            report.verification_results
        ), 1):
            if verification.status == VerificationStatus.ACCURATE:
                continue

            label = self.STATUS_LABELS_JA.get(verification.status, verification.status.value)

            lines.append("")
            lines.append(f"[{i}] {citation.raw_text}")
            lines.append(f"    ステータス: {label}")

            if citation.claim_text:
                claim_short = citation.claim_text[:80] + "..." if len(citation.claim_text) > 80 else citation.claim_text
                lines.append(f"    主張: {claim_short}")

            if verification.issues:
                for issue in verification.issues:
                    lines.append(f"    → {issue.description}")

            if verification.recommendations:
                lines.append(f"    推奨: {verification.recommendations[0]}")

        # 正確な引用の数を表示
        accurate_count = sum(
            1 for v in report.verification_results
            if v.status == VerificationStatus.ACCURATE
        )
        if accurate_count > 0:
            lines.append("")
            lines.append(f"[その他 {accurate_count} 件の引用は問題なし]")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


def generate_report(
    draft_text: str,
    parsed_draft: ParsedDraft,
    match_results: List[MatchResult],
    verification_results: List[VerificationResult],
    format: str = "markdown"
) -> str:
    """レポートを生成（簡易関数）"""
    report = VerificationReport(
        draft_text, parsed_draft, match_results, verification_results
    )
    generator = ReportGenerator()

    if format == "json":
        return generator.generate_json(report)
    elif format == "console":
        return generator.generate_console(report)
    else:
        return generator.generate_markdown(report)
