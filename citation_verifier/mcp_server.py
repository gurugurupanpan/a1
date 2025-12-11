#!/usr/bin/env python3
"""
Citation Verification MCP Server
ClaudeがZoteroのPDFを参照して引用を検証できるようにするMCPサーバー
"""

import json
import sys
from pathlib import Path
from typing import Optional

# MCPサーバーの基本構造
class CitationVerifierMCP:
    """MCP Server for Citation Verification"""

    def __init__(self, zotero_path: Optional[str] = None):
        self.zotero_path = zotero_path or self._find_zotero_path()

    def _find_zotero_path(self) -> Optional[str]:
        """Zoteroのデフォルトパスを探す"""
        possible_paths = [
            Path.home() / "Zotero" / "storage",
            Path.home() / "Documents" / "Zotero" / "storage",
            Path("/Users") / "*/Zotero/storage",
        ]
        for path in possible_paths:
            if path.exists():
                return str(path)
        return None

    def get_tools(self):
        """利用可能なツールを返す"""
        return [
            {
                "name": "check_citations",
                "description": "論文ドラフトから引用を検出し、一覧表示する",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "検証する論文テキスト"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "verify_claim",
                "description": "特定の主張を元論文PDFと照合して検証する",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": "検証する主張"
                        },
                        "author": {
                            "type": "string",
                            "description": "著者名（PDFを検索するため）"
                        },
                        "year": {
                            "type": "integer",
                            "description": "出版年"
                        }
                    },
                    "required": ["claim"]
                }
            },
            {
                "name": "search_pdf",
                "description": "Zoteroフォルダ内のPDFを検索",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "検索キーワード（著者名、タイトルの一部など）"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "read_pdf_section",
                "description": "PDFの特定セクションを読み取る",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pdf_path": {
                            "type": "string",
                            "description": "PDFファイルのパス"
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "検索するキーワード"
                        }
                    },
                    "required": ["pdf_path"]
                }
            }
        ]

    def call_tool(self, name: str, arguments: dict):
        """ツールを実行"""
        if name == "check_citations":
            return self._check_citations(arguments.get("text", ""))
        elif name == "verify_claim":
            return self._verify_claim(
                arguments.get("claim", ""),
                arguments.get("author"),
                arguments.get("year")
            )
        elif name == "search_pdf":
            return self._search_pdf(arguments.get("query", ""))
        elif name == "read_pdf_section":
            return self._read_pdf_section(
                arguments.get("pdf_path", ""),
                arguments.get("keywords", [])
            )
        else:
            return {"error": f"Unknown tool: {name}"}

    def _check_citations(self, text: str) -> dict:
        """引用をチェック"""
        try:
            # 親ディレクトリをパスに追加
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from citation_verifier import quick_check, list_citations

            citations = list_citations(text)
            summary = quick_check(text)

            return {
                "citations_found": len(citations),
                "citations": citations,
                "summary": summary
            }
        except Exception as e:
            return {"error": str(e)}

    def _verify_claim(self, claim: str, author: Optional[str], year: Optional[int]) -> dict:
        """主張を検証"""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from citation_verifier import analyze_claim
            from citation_verifier.google_drive import LocalZoteroStorage

            # PDFを検索
            if not self.zotero_path:
                return {"error": "Zoteroパスが設定されていません"}

            storage = LocalZoteroStorage(self.zotero_path)

            # 著者名や年でPDFを検索
            search_terms = []
            if author:
                search_terms.append(author.lower())
            if year:
                search_terms.append(str(year))

            if search_terms:
                all_pdfs = storage.list_pdfs()
                matching_pdfs = [
                    pdf for pdf in all_pdfs
                    if all(term in pdf.name.lower() for term in search_terms)
                ]

                if matching_pdfs:
                    result = analyze_claim(claim, str(matching_pdfs[0]))
                    result["matched_pdf"] = str(matching_pdfs[0])
                    return result
                else:
                    return {
                        "error": "該当するPDFが見つかりませんでした",
                        "search_terms": search_terms
                    }
            else:
                return {"error": "著者名または年を指定してください"}

        except Exception as e:
            return {"error": str(e)}

    def _search_pdf(self, query: str) -> dict:
        """PDFを検索"""
        try:
            if not self.zotero_path:
                return {"error": "Zoteroパスが設定されていません"}

            sys.path.insert(0, str(Path(__file__).parent.parent))
            from citation_verifier.google_drive import LocalZoteroStorage

            storage = LocalZoteroStorage(self.zotero_path)
            results = storage.search_pdf_by_name(query)

            return {
                "found": len(results),
                "pdfs": [str(p) for p in results[:20]]  # 最大20件
            }
        except Exception as e:
            return {"error": str(e)}

    def _read_pdf_section(self, pdf_path: str, keywords: list) -> dict:
        """PDFのセクションを読む"""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from citation_verifier.pdf_parser import PDFParser

            parser = PDFParser()
            doc = parser.parse(pdf_path)

            if keywords:
                excerpts = doc.search_sentences(keywords, max_results=5)
                return {
                    "title": doc.metadata.title,
                    "author": doc.metadata.author,
                    "excerpts": [
                        {"page": page, "text": text[:500]}
                        for page, text in excerpts
                    ]
                }
            else:
                # キーワードなしの場合は最初の部分を返す
                return {
                    "title": doc.metadata.title,
                    "author": doc.metadata.author,
                    "first_page": doc.pages[0].text[:1000] if doc.pages else ""
                }
        except Exception as e:
            return {"error": str(e)}


def main():
    """MCPサーバーのエントリポイント"""
    import os

    # 環境変数からZoteroパスを取得
    zotero_path = os.environ.get("ZOTERO_PATH")

    server = CitationVerifierMCP(zotero_path)

    # 標準入出力でJSONRPCを処理
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method = request.get("method")

            if method == "tools/list":
                response = {"tools": server.get_tools()}
            elif method == "tools/call":
                params = request.get("params", {})
                result = server.call_tool(
                    params.get("name"),
                    params.get("arguments", {})
                )
                response = {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
            else:
                response = {"error": f"Unknown method: {method}"}

            print(json.dumps({"id": request.get("id"), "result": response}))
            sys.stdout.flush()

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
