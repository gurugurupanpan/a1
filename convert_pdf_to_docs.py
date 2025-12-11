#!/usr/bin/env python3
"""
PDF to Google Docs Converter

This script converts all PDF files in a source Google Drive folder
to Google Docs format and saves them to a destination folder.

Authentication Setup:
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API
4. Create credentials:
   - For Service Account (recommended for server use):
     - Create Service Account, download JSON key
     - Share source/destination folders with service account email
     - Set GOOGLE_SERVICE_ACCOUNT_KEY environment variable or save as service_account.json

   - For OAuth 2.0 (for personal use):
     - Create OAuth 2.0 Client ID (Desktop app)
     - Download credentials.json
     - Run script and authorize via browser
"""

import os
import sys
import io
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required for Google Drive operations
SCOPES = ['https://www.googleapis.com/auth/drive']

# Folder IDs from the URLs
SOURCE_FOLDER_ID = '13neUxNQTzXGHnHXqvHc8qYUvFPdy1Qqw'
DEST_FOLDER_ID = '1VhIZTrpqwaWphlUW_mHVRLzb41F_1uZ3'


def get_service_account_credentials():
    """Get credentials from service account JSON file."""
    # Check for service account key in environment variable
    key_content = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')

    if key_content:
        import json
        key_data = json.loads(key_content)
        credentials = service_account.Credentials.from_service_account_info(
            key_data, scopes=SCOPES
        )
        return credentials

    # Check for service account JSON file
    key_files = ['service_account.json', 'credentials_service_account.json']
    for key_file in key_files:
        if os.path.exists(key_file):
            credentials = service_account.Credentials.from_service_account_file(
                key_file, scopes=SCOPES
            )
            return credentials

    return None


def get_oauth_credentials():
    """Get credentials using OAuth 2.0 flow."""
    creds = None

    # Check for existing token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds


def get_credentials():
    """Get credentials using available method."""
    # Try service account first
    creds = get_service_account_credentials()
    if creds:
        print("Using service account credentials")
        return creds

    # Try OAuth
    creds = get_oauth_credentials()
    if creds:
        print("Using OAuth credentials")
        return creds

    return None


def extract_folder_id(url_or_id):
    """Extract folder ID from URL or return ID as-is."""
    if 'drive.google.com' in url_or_id:
        # Extract ID from URL
        if '/folders/' in url_or_id:
            return url_or_id.split('/folders/')[-1].split('?')[0].split('/')[0]
    return url_or_id


def list_pdfs_in_folder(service, folder_id):
    """List all PDF files in a Google Drive folder."""
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=100
    ).execute()

    return results.get('files', [])


def convert_pdf_to_docs(service, pdf_file, dest_folder_id):
    """
    Convert a PDF file to Google Docs format.

    Google Drive API allows importing PDF as Google Docs by copying with conversion.
    """
    pdf_id = pdf_file['id']
    pdf_name = pdf_file['name']

    # Remove .pdf extension for the Docs name
    docs_name = pdf_name
    if docs_name.lower().endswith('.pdf'):
        docs_name = docs_name[:-4]

    print(f"  Converting: {pdf_name} -> {docs_name}")

    try:
        # Method: Copy the file with conversion to Google Docs format
        # First, we need to download and re-upload with conversion

        # Download the PDF
        request = service.files().get_media(fileId=pdf_id)
        pdf_content = io.BytesIO()
        downloader = MediaIoBaseDownload(pdf_content, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        pdf_content.seek(0)

        # Save temporarily
        temp_file = f'/tmp/{pdf_name}'
        with open(temp_file, 'wb') as f:
            f.write(pdf_content.read())

        # Upload with conversion to Google Docs
        file_metadata = {
            'name': docs_name,
            'parents': [dest_folder_id],
            'mimeType': 'application/vnd.google-apps.document'
        }

        media = MediaFileUpload(
            temp_file,
            mimetype='application/pdf',
            resumable=True
        )

        created_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()

        # Clean up temp file
        os.remove(temp_file)

        print(f"    Created: {created_file.get('name')}")
        print(f"    Link: {created_file.get('webViewLink')}")

        return created_file

    except Exception as e:
        print(f"    Error converting {pdf_name}: {str(e)}")
        return None


def main():
    """Main function to convert all PDFs in source folder to Docs in destination folder."""
    print("=" * 60)
    print("PDF to Google Docs Converter")
    print("=" * 60)

    # Get credentials
    creds = get_credentials()

    if not creds:
        print("\nError: No valid credentials found!")
        print("\nPlease set up authentication using one of these methods:")
        print("\n1. Service Account (Recommended for automation):")
        print("   - Create a service account in Google Cloud Console")
        print("   - Download the JSON key file")
        print("   - Save it as 'service_account.json' in this directory")
        print("   - OR set GOOGLE_SERVICE_ACCOUNT_KEY environment variable")
        print("   - Share both Drive folders with the service account email")
        print("\n2. OAuth 2.0 (For personal use):")
        print("   - Create OAuth 2.0 credentials in Google Cloud Console")
        print("   - Download and save as 'credentials.json'")
        print("   - Run this script again to authorize via browser")
        sys.exit(1)

    # Build the Drive service
    service = build('drive', 'v3', credentials=creds)

    print(f"\nSource folder ID: {SOURCE_FOLDER_ID}")
    print(f"Destination folder ID: {DEST_FOLDER_ID}")

    # Verify access to folders
    print("\nVerifying folder access...")
    try:
        source_info = service.files().get(fileId=SOURCE_FOLDER_ID, fields='name').execute()
        print(f"  Source folder: {source_info.get('name')}")
    except Exception as e:
        print(f"  Error accessing source folder: {e}")
        print("  Please share the source folder with your service account email")
        sys.exit(1)

    try:
        dest_info = service.files().get(fileId=DEST_FOLDER_ID, fields='name').execute()
        print(f"  Destination folder: {dest_info.get('name')}")
    except Exception as e:
        print(f"  Error accessing destination folder: {e}")
        print("  Please share the destination folder with your service account email")
        sys.exit(1)

    # List PDFs in source folder
    print("\nListing PDF files in source folder...")
    pdfs = list_pdfs_in_folder(service, SOURCE_FOLDER_ID)

    if not pdfs:
        print("No PDF files found in the source folder.")
        return

    print(f"Found {len(pdfs)} PDF file(s):")
    for pdf in pdfs:
        print(f"  - {pdf['name']}")

    # Convert each PDF
    print("\n" + "=" * 60)
    print("Starting conversion...")
    print("=" * 60)

    successful = 0
    failed = 0

    for i, pdf in enumerate(pdfs, 1):
        print(f"\n[{i}/{len(pdfs)}] Processing: {pdf['name']}")
        result = convert_pdf_to_docs(service, pdf, DEST_FOLDER_ID)

        if result:
            successful += 1
        else:
            failed += 1

        # Small delay to avoid rate limiting
        if i < len(pdfs):
            time.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("Conversion Complete!")
    print("=" * 60)
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(pdfs)}")
    print(f"\nConverted files are in:")
    print(f"  https://drive.google.com/drive/folders/{DEST_FOLDER_ID}")


if __name__ == '__main__':
    main()
