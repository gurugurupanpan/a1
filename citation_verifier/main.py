"""
Citation Verification Tool - メインエントリポイント
論文ドラフトの引用を検証し、誤引用・誇張・逆の結果を検出する
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List

from .config import Config, get_config
from .citation_parser import CitationParser, CitationStyle
from .pdf_parser import PDFParser
from .matcher import PDFMatcher, ReferenceListMatcher
from .verifier import CitationVerifier
from .reporter import generate_report, VerificationReport, ReportGenerator


class CitationVerificationTool:
    """引用検証ツールのメインクラス"""

    def __init__(
        self,
        zotero_path: Optional[str] = None,
        use_google_drive: bool = False,
        credentials_path: Optional[str] = None,
        zotero_folder_id: Optional[str] = None
    ):
        """
        初期化

        Args:
            zotero_path: ローカルのZoteroストレージパス
            use_google_drive: Google Driveを使用するか
            credentials_path: Google Drive認証情報のパス
            zotero_folder_id: Google Drive内のZoteroフォルダID
        """
        self.config = get_config()

        # Zoteroパスの設定
        self.zotero_path = zotero_path or self.config.zotero_local_path
        self.use_google_drive = use_google_drive
        self.credentials_path = credentials_path or self.config.google_drive_credentials_path
        self.zotero_folder_id = zotero_folder_id or self.config.zotero_folder_id

        # コンポーネント初期化
        self.citation_parser = CitationParser()
        self.verifier = CitationVerifier()
        self.reference_matcher = ReferenceListMatcher()

        # PDFマッチャーは遅延初期化
        self._pdf_matcher: Optional[PDFMatcher] = None

    @property
    def pdf_matcher(self) -> PDFMatcher:
        """PDFマッチャーを取得（遅延初期化）"""
        if self._pdf_matcher is None:
            self._pdf_matcher = PDFMatcher(
                use_google_drive=self.use_google_drive,
                local_path=self.zotero_path,
                credentials_path=self.credentials_path,
                zotero_folder_id=self.zotero_folder_id
            )
        return self._pdf_matcher

    def verify_text(
        self,
        draft_text: str,
        reference_list: Optional[str] = None,
        output_format: str = "markdown"
    ) -> str:
        """
        論文ドラフトの引用を検証

        Args:
            draft_text: 論文ドラフトのテキスト
            reference_list: 参考文献リスト（番号引用の場合）
            output_format: 出力形式 ("markdown", "json", "console")

        Returns:
            検証レポート
        """
        # 1. 引用をパース
        parsed = self.citation_parser.parse(draft_text)

        if not parsed.citations:
            return "引用が検出されませんでした。"

        print(f"検出された引用: {len(parsed.citations)} 件")
        print(f"引用スタイル: {parsed.detected_style.value}")

        # 2. 参考文献リストがあればパース
        if reference_list:
            self.reference_matcher.parse_reference_list(reference_list)

        # 3. 各引用をPDFとマッチング
        print("PDFとのマッチングを実行中...")
        match_results = self.pdf_matcher.match_all_citations(parsed.citations)

        matched_count = sum(1 for m in match_results if m.matched_pdf)
        print(f"マッチング成功: {matched_count} / {len(parsed.citations)} 件")

        # 4. 各引用を検証
        print("引用内容を検証中...")
        verification_results = []

        for citation, match in zip(parsed.citations, match_results):
            result = self.verifier.verify_citation(
                claim_text=citation.claim_text or citation.context,
                source_document=match.pdf_document
            )
            verification_results.append(result)

        # 5. レポート生成
        report = generate_report(
            draft_text=draft_text,
            parsed_draft=parsed,
            match_results=match_results,
            verification_results=verification_results,
            format=output_format
        )

        return report

    def verify_file(
        self,
        draft_file: str,
        reference_file: Optional[str] = None,
        output_format: str = "markdown"
    ) -> str:
        """
        ファイルから論文ドラフトを読み込んで検証

        Args:
            draft_file: ドラフトファイルのパス
            reference_file: 参考文献ファイルのパス
            output_format: 出力形式

        Returns:
            検証レポート
        """
        draft_path = Path(draft_file)
        if not draft_path.exists():
            raise FileNotFoundError(f"File not found: {draft_file}")

        draft_text = draft_path.read_text(encoding='utf-8')

        reference_list = None
        if reference_file:
            ref_path = Path(reference_file)
            if ref_path.exists():
                reference_list = ref_path.read_text(encoding='utf-8')

        return self.verify_text(draft_text, reference_list, output_format)

    def quick_check(self, text: str) -> str:
        """
        素早い引用チェック（PDFマッチングなし）

        Args:
            text: チェックするテキスト

        Returns:
            簡易チェック結果
        """
        parsed = self.citation_parser.parse(text)

        if not parsed.citations:
            return "引用が検出されませんでした。"

        lines = [
            f"検出された引用: {len(parsed.citations)} 件",
            f"引用スタイル: {parsed.detected_style.value}",
            ""
        ]

        for i, citation in enumerate(parsed.citations, 1):
            lines.append(f"{i}. {citation.raw_text}")
            if citation.authors:
                lines.append(f"   著者: {', '.join(citation.authors)}")
            if citation.year:
                lines.append(f"   年: {citation.year}")
            if citation.claim_text:
                claim_short = citation.claim_text[:100]
                lines.append(f"   主張: {claim_short}...")
            lines.append("")

        return "\n".join(lines)


def main():
    """CLIエントリポイント"""
    parser = argparse.ArgumentParser(
        description="論文ドラフトの引用を検証し、誤引用・誇張・逆の結果を検出する"
    )

    parser.add_argument(
        'action',
        choices=['verify', 'check', 'config'],
        help='実行するアクション'
    )

    parser.add_argument(
        '-t', '--text',
        help='検証するテキスト（直接指定）'
    )

    parser.add_argument(
        '-f', '--file',
        help='検証するファイル'
    )

    parser.add_argument(
        '-r', '--references',
        help='参考文献リストファイル'
    )

    parser.add_argument(
        '-o', '--output',
        choices=['markdown', 'json', 'console'],
        default='console',
        help='出力形式'
    )

    parser.add_argument(
        '--zotero-path',
        help='ZoteroのローカルストレージパスPath'
    )

    parser.add_argument(
        '--google-drive',
        action='store_true',
        help='Google Driveを使用'
    )

    parser.add_argument(
        '--credentials',
        help='Google Drive認証情報ファイル'
    )

    parser.add_argument(
        '--folder-id',
        help='Google DriveのZoteroフォルダID'
    )

    args = parser.parse_args()

    # 設定アクション
    if args.action == 'config':
        config = get_config()
        print("現在の設定:")
        print(f"  Zoteroローカルパス: {config.zotero_local_path}")
        print(f"  Google Drive認証: {config.google_drive_credentials_path}")
        print(f"  ZoteroフォルダID: {config.zotero_folder_id}")
        print(f"  キャッシュディレクトリ: {config.cache_dir}")
        return

    # ツール初期化
    tool = CitationVerificationTool(
        zotero_path=args.zotero_path,
        use_google_drive=args.google_drive,
        credentials_path=args.credentials,
        zotero_folder_id=args.folder_id
    )

    # テキストを取得
    text = None
    if args.text:
        text = args.text
    elif args.file:
        text = Path(args.file).read_text(encoding='utf-8')
    else:
        # 標準入力から読み込み
        print("検証するテキストを入力してください（Ctrl+Dで終了）:")
        text = sys.stdin.read()

    if not text.strip():
        print("テキストが空です。")
        return

    # アクション実行
    if args.action == 'check':
        result = tool.quick_check(text)
    else:  # verify
        result = tool.verify_text(
            text,
            reference_list=Path(args.references).read_text() if args.references else None,
            output_format=args.output
        )

    print(result)


if __name__ == '__main__':
    main()
