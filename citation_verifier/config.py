"""
設定管理モジュール
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

CONFIG_FILE = Path.home() / ".citation_verifier" / "config.json"


@dataclass
class Config:
    """アプリケーション設定"""
    # Google Drive設定
    google_drive_credentials_path: Optional[str] = None
    zotero_folder_id: Optional[str] = None  # Google Drive内のZoteroフォルダID
    zotero_local_path: Optional[str] = None  # ローカルのZoteroストレージパス

    # キャッシュ設定
    cache_dir: str = field(default_factory=lambda: str(Path.home() / ".citation_verifier" / "cache"))

    # PDF解析設定
    pdf_extraction_method: str = "pymupdf"  # "pymupdf" or "pdfplumber"

    # 検証設定
    similarity_threshold: float = 0.7  # 類似度閾値
    context_window: int = 500  # 引用周辺のコンテキスト文字数

    @classmethod
    def load(cls) -> "Config":
        """設定ファイルから読み込み"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        return cls()

    def save(self) -> None:
        """設定ファイルに保存"""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, indent=2, ensure_ascii=False)


def get_config() -> Config:
    """設定を取得"""
    return Config.load()
