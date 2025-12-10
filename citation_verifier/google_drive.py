"""
Google Drive API連携モジュール
ZoteroフォルダからPDFを取得する
"""

import os
import io
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

from .config import get_config

# Google Drive APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


@dataclass
class DriveFile:
    """Google Drive上のファイル情報"""
    id: str
    name: str
    mime_type: str
    parents: List[str]
    size: Optional[int] = None
    modified_time: Optional[str] = None


class GoogleDriveClient:
    """Google Drive APIクライアント"""

    def __init__(self, credentials_path: Optional[str] = None):
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. "
                "Run: pip install google-auth-oauthlib google-api-python-client"
            )

        self.config = get_config()
        self.credentials_path = credentials_path or self.config.google_drive_credentials_path
        self.token_path = Path.home() / ".citation_verifier" / "token.json"
        self.service = None

    def authenticate(self) -> None:
        """Google Drive APIの認証を行う"""
        creds = None

        # 既存のトークンを読み込み
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # トークンが無効または期限切れの場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path:
                    raise ValueError(
                        "Google Drive credentials path not set. "
                        "Set it in config or pass to constructor."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # トークンを保存
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('drive', 'v3', credentials=creds)

    def list_pdfs_in_folder(
        self,
        folder_id: Optional[str] = None,
        recursive: bool = True
    ) -> List[DriveFile]:
        """
        指定フォルダ内のPDFファイルを一覧取得

        Args:
            folder_id: GoogleドライブのフォルダID（Noneの場合は設定から取得）
            recursive: サブフォルダも含めて検索するか

        Returns:
            PDFファイルのリスト
        """
        if not self.service:
            self.authenticate()

        folder_id = folder_id or self.config.zotero_folder_id
        if not folder_id:
            raise ValueError("Zotero folder ID not set in config")

        pdf_files = []
        folders_to_search = [folder_id]

        while folders_to_search:
            current_folder = folders_to_search.pop(0)

            # PDFファイルを検索
            query = f"'{current_folder}' in parents and mimeType='application/pdf' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, parents, size, modifiedTime)',
                pageSize=1000
            ).execute()

            for file in results.get('files', []):
                pdf_files.append(DriveFile(
                    id=file['id'],
                    name=file['name'],
                    mime_type=file['mimeType'],
                    parents=file.get('parents', []),
                    size=file.get('size'),
                    modified_time=file.get('modifiedTime')
                ))

            # サブフォルダを検索
            if recursive:
                folder_query = f"'{current_folder}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                folder_results = self.service.files().list(
                    q=folder_query,
                    spaces='drive',
                    fields='files(id, name)',
                    pageSize=1000
                ).execute()

                for folder in folder_results.get('files', []):
                    folders_to_search.append(folder['id'])

        return pdf_files

    def download_pdf(self, file_id: str, destination: Optional[Path] = None) -> bytes:
        """
        PDFファイルをダウンロード

        Args:
            file_id: ファイルID
            destination: 保存先パス（Noneの場合はバイトデータを返す）

        Returns:
            PDFのバイトデータ
        """
        if not self.service:
            self.authenticate()

        request = self.service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        pdf_data = buffer.getvalue()

        if destination:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(destination, 'wb') as f:
                f.write(pdf_data)

        return pdf_data

    def search_pdf_by_name(self, name_pattern: str, folder_id: Optional[str] = None) -> List[DriveFile]:
        """
        名前でPDFを検索

        Args:
            name_pattern: 検索パターン（部分一致）
            folder_id: 検索対象フォルダ

        Returns:
            マッチしたファイルのリスト
        """
        if not self.service:
            self.authenticate()

        folder_id = folder_id or self.config.zotero_folder_id

        query_parts = [
            f"name contains '{name_pattern}'",
            "mimeType='application/pdf'",
            "trashed=false"
        ]

        if folder_id:
            # フォルダ内とそのサブフォルダを検索
            # 注: Google Drive APIは直接的なサブフォルダ検索をサポートしていないため、
            # フルスキャンから絞り込む
            all_pdfs = self.list_pdfs_in_folder(folder_id, recursive=True)
            return [
                pdf for pdf in all_pdfs
                if name_pattern.lower() in pdf.name.lower()
            ]

        query = " and ".join(query_parts)
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, parents, size, modifiedTime)',
            pageSize=100
        ).execute()

        return [
            DriveFile(
                id=file['id'],
                name=file['name'],
                mime_type=file['mimeType'],
                parents=file.get('parents', []),
                size=file.get('size'),
                modified_time=file.get('modifiedTime')
            )
            for file in results.get('files', [])
        ]


class LocalZoteroStorage:
    """ローカルのZoteroストレージを扱うクラス"""

    def __init__(self, storage_path: Optional[str] = None):
        self.config = get_config()
        self.storage_path = Path(storage_path or self.config.zotero_local_path or "")

    def list_pdfs(self) -> List[Path]:
        """ストレージ内の全PDFを一覧"""
        if not self.storage_path.exists():
            raise FileNotFoundError(f"Zotero storage path not found: {self.storage_path}")

        return list(self.storage_path.rglob("*.pdf"))

    def search_pdf_by_name(self, name_pattern: str) -> List[Path]:
        """名前でPDFを検索"""
        all_pdfs = self.list_pdfs()
        pattern_lower = name_pattern.lower()
        return [pdf for pdf in all_pdfs if pattern_lower in pdf.name.lower()]

    def read_pdf(self, pdf_path: Path) -> bytes:
        """PDFファイルを読み込み"""
        with open(pdf_path, 'rb') as f:
            return f.read()
