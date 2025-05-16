import argparse
import os
import json
import re
import jieba
import jieba.posseg as pseg
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pypinyin import pinyin, Style
from deep_translator import GoogleTranslator

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            return creds
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    return creds

def get_or_create_folder(drive_service, folder_name):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    result = drive_service.files().list(q=query, spaces='drive', fields="files(id)").execute()
    folders = result.get('files', [])
    if folders:
        return folders[0]['id']
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def create_sheet(sheets_service, drive_service, title, folder_id):
    sheet = sheets_service.spreadsheets().create(body={
        'properties': {'title': title}
    }).execute()
    sheet_id = sheet['spreadsheetId']
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_info = sheet_metadata['sheets'][0]['properties']
    sheet_name = sheet_info['title']
    sheet_gid = sheet_info['sheetId']

    drive_service.files().update(
        fileId=sheet_id,
        addParents=folder_id,
        fields='id, parents'
    ).execute()

    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A1:C1",
        valueInputOption='RAW',
        body={"values": [["front", "back", "pinyin"]]}
    ).execute()

    return sheet_id, sheet_name, sheet_gid

def create_keyword_sheet(sheets_service, drive_service, folder_id, title, lines):
    keywords = set()
    for _, chinese, _ in lines:
        for word, flag in pseg.cut(chinese):
            if flag.startswith('n') or flag.startswith('v'):
                keywords.add(word)

    keyword_data = []
    for word in sorted(keywords):
        pinyin_text = generate_pinyin_by_word(word)
        translation = translate_to_korean(word)
        keyword_data.append([translation, word, pinyin_text])

    sheet_id, sheet_name, sheet_gid = create_sheet(
        sheets_service, drive_service,
        title=f"Keywords_{title}",
        folder_id=folder_id
    )

    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A2:C",
        valueInputOption='RAW',
        body={"values": keyword_data}
    ).execute()

    resize_columns(sheets_service, sheet_id, sheet_gid)

def resize_columns(sheets_service, spreadsheet_id, sheet_gid):
    requests = [
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_gid,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 3
                }
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_gid,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 3
                },
                "properties": {
                    "pixelSize": 250
                },
                "fields": "pixelSize"
            }
        }
    ]
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests}
    ).execute()

def generate_pinyin_by_word(text):
    words = jieba.cut(str(text))
    result = []
    for word in words:
        p = pinyin(word, style=Style.TONE)
        result.append(''.join(item[0] for item in p))
    return ' '.join(result)

def translate_to_korean(text):
    try:
        return GoogleTranslator(source='zh', target='ko').translate(text)
    except Exception:
        try:
            return GoogleTranslator(source='auto', target='ko').translate(text)
        except Exception as e:
            print(f"[번역 실패] {text} → {e}")
            return ""

def extract_lines_from_doc(docs_service, doc_id):
    doc = docs_service.documents().get(documentId=doc_id).execute()
    lines = []
    for content in doc.get('body').get('content', []):
        if 'paragraph' in content:
            for el in content['paragraph'].get('elements', []):
                txt = el.get('textRun', {}).get('content', '')
                if txt.strip():
                    cleaned = re.sub(r'\(.*?\)', '', txt).strip()
                    pinyin_flat = generate_pinyin_by_word(cleaned)
                    translated = translate_to_korean(cleaned)
                    lines.append([translated, cleaned, pinyin_flat])
    return lines

def write_to_sheet(sheets_service, sheet_id, sheet_name, lines):
    range_to_write = f"{sheet_name}!A2:C"
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_to_write,
        valueInputOption='RAW',
        body={"values": lines}
    ).execute()

def save_meta(doc_id, sheet_id, doc_title, sheet_title):
    with open('meta.json', 'w') as f:
        json.dump({
            "doc_id": doc_id,
            "sheet_id": sheet_id,
            "doc_title": doc_title,
            "sheet_title": sheet_title
        }, f, indent=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--doc-id', help='직접 만든 Google Docs 문서 ID를 입력하세요')
    args = parser.parse_args()

    creds = get_credentials()
    docs_service = build('docs', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    folder_id = get_or_create_folder(drive_service, "중국어 공부")
    today = datetime.now().strftime("%m%d")
    now_time = datetime.now().strftime("%H:%M")

    if args.doc_id:
        doc_id = args.doc_id
        doc = docs_service.documents().get(documentId=doc_id).execute()
        doc_title = doc.get('title')
        safe_doc_title = doc_title.replace('/', '-').replace(' ', '_') + f"-{now_time}"
        sheet_title = f"Chinese_{today}_from_{safe_doc_title}"
        sheet_id, sheet_name, sheet_gid = create_sheet(sheets_service, drive_service, sheet_title, folder_id)
        lines = extract_lines_from_doc(docs_service, doc_id)
        write_to_sheet(sheets_service, sheet_id, sheet_name, lines)
        resize_columns(sheets_service, sheet_id, sheet_gid)
        create_keyword_sheet(sheets_service, drive_service, folder_id, sheet_title, lines)
        save_meta(doc_id, sheet_id, doc_title, sheet_title)
        print(f"✅ 기존 문서 사용 완료")
    else:
        doc_title = datetime.now().strftime("%m/%d")
        doc = docs_service.documents().create(body={'title': doc_title}).execute()
        doc_id = doc.get('documentId')
        sheet_title = f"Chinese_{today}"
        sheet_id, sheet_name, sheet_gid = create_sheet(sheets_service, drive_service, sheet_title, folder_id)
        resize_columns(sheets_service, sheet_id, sheet_gid)
        save_meta(doc_id, sheet_id, doc_title, sheet_title)
        print(f"✅ 새 문서/시트 생성 완료")

    print(f"📄 Docs: https://docs.google.com/document/d/{doc_id}/edit")
    print(f"📊 Sheet: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")

if __name__ == '__main__':
    main()
