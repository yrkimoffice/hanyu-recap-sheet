import argparse
import os
import json
import re
import jieba
import jieba.posseg as pseg
from time import time
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

class HanyuRecapSheet:
    def __init__(self, doc_id=None):
        self.doc_id = doc_id
        self.creds = self.get_credentials()
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.folder_id = self.get_or_create_folder("중국어 공부")
        self.today = datetime.now().strftime("%m%d")
        self.now_time = datetime.now().strftime("%H:%M")

    def get_credentials(self):
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

    def get_or_create_folder(self, folder_name):
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        result = self.drive_service.files().list(q=query, spaces='drive', fields="files(id)").execute()
        folders = result.get('files', [])
        if folders:
            return folders[0]['id']
        folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')

    def create_sheet(self, title):
        sheet = self.sheets_service.spreadsheets().create(body={'properties': {'title': title}}).execute()
        sheet_id = sheet['spreadsheetId']
        sheet_metadata = self.sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheet_info = sheet_metadata['sheets'][0]['properties']
        sheet_name = sheet_info['title']
        sheet_gid = sheet_info['sheetId']

        self.drive_service.files().update(fileId=sheet_id, addParents=self.folder_id, fields='id, parents').execute()

        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A1:C1",
            valueInputOption='RAW',
            body={"values": [["front", "back", "pinyin"]]}
        ).execute()

        return sheet_id, sheet_name, sheet_gid

    def resize_columns(self, spreadsheet_id, sheet_gid):
        requests = [
            {"autoResizeDimensions": {"dimensions": {"sheetId": sheet_gid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 3}}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_gid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 3}, "properties": {"pixelSize": 250}, "fields": "pixelSize"}}
        ]
        self.sheets_service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()

    def generate_pinyin(self, text):
        words = jieba.cut(str(text))
        result = []
        for word in words:
            p = pinyin(word, style=Style.TONE)
            result.append(''.join(item[0] for item in p))
        return ' '.join(result)

    def translate(self, text):
        try:
            return GoogleTranslator(source='zh', target='ko').translate(text)
        except Exception:
            try:
                return GoogleTranslator(source='auto', target='ko').translate(text)
            except Exception as e:
                print(f"[번역 실패] {text} → {e}")
                return ""

    def extract_lines_from_doc(self):
        doc = self.docs_service.documents().get(documentId=self.doc_id).execute()
        self.doc_title = doc.get('title')
        lines = []
        for content in doc.get('body').get('content', []):
            if 'paragraph' in content:
                for el in content['paragraph'].get('elements', []):
                    txt = el.get('textRun', {}).get('content', '')
                    if txt.strip():
                        cleaned = re.sub(r'\(.*?\)', '', txt).strip()
                        pinyin_flat = self.generate_pinyin(cleaned)
                        translated = self.translate(cleaned)
                        if cleaned and not cleaned.startswith(('#', '//')):
                            lines.append([translated, cleaned, pinyin_flat])
        return lines

    def write_to_sheet(self, sheet_id, sheet_name, lines):
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A2:C",
            valueInputOption='RAW',
            body={"values": lines}
        ).execute()

    def create_keyword_sheet(self, title, lines):
        keywords = set()
        for _, chinese, _ in lines:
            for word, flag in pseg.cut(chinese):
                if flag.startswith('n') or flag.startswith('v'):
                    keywords.add(word)

        keyword_data = []
        for word in sorted(keywords):
            pinyin_text = self.generate_pinyin(word)
            translation = self.translate(word)
            keyword_data.append([translation, word, pinyin_text])

        sheet_id, sheet_name, sheet_gid = self.create_sheet(f"Keywords_{title}")
        self.write_to_sheet(sheet_id, sheet_name, keyword_data)
        self.resize_columns(sheet_id, sheet_gid)

    def save_meta(self, sheet_id, sheet_title):
        with open('meta.json', 'w') as f:
            json.dump({
                "doc_id": self.doc_id,
                "sheet_id": sheet_id,
                "doc_title": self.doc_title,
                "sheet_title": sheet_title
            }, f, indent=2)


    def run(self):
            start = time()
            if not self.doc_id:
                doc_title = f"{datetime.now().strftime('%m/%d')} - 중국어 정리"
                doc = self.docs_service.documents().create(body={'title': doc_title}).execute()
                self.doc_id = doc.get('documentId')
                self.doc_title = doc_title
            else:
                doc = self.docs_service.documents().get(documentId=self.doc_id).execute()
                self.doc_title = doc.get('title')

            safe_doc_title = self.doc_title.replace('/', '-').replace(' ', '_') + f"-{self.now_time}"
            sheet_title = f"Chinese_{self.today}_from_{safe_doc_title}"
            sheet_id, sheet_name, sheet_gid = self.create_sheet(sheet_title)
            try:
                lines = self.extract_lines_from_doc()
            except Exception as e:
                print(f"❌ 문서를 불러올 수 없습니다: {e}")
                return
            
            self.write_to_sheet(sheet_id, sheet_name, lines)
            self.resize_columns(sheet_id, sheet_gid)
            self.create_keyword_sheet(sheet_title, lines)
            self.save_meta(sheet_id, sheet_title)

            print(f"✅ 문장 {len(lines)}개 처리 완료")
            print(f"📄 Docs: https://docs.google.com/document/d/{self.doc_id}/edit")
            print(f"📊 Sheet: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
            with open('history.log', 'a') as log:
                log.write(f"{datetime.now()} - {self.doc_title} → {sheet_title} | 문장: {len(lines)}")
            print(f"⏱️ 처리 시간: {round(time() - start, 2)}초")

if __name__ == '__main__':
    use_existing = input("기존에 docs가 있습니까? (y/n): ").strip().lower()
    doc_id = None

    if use_existing == 'y':
        doc_id = input("문서 ID를 입력하세요: ").strip()

    bot = HanyuRecapSheet(doc_id=doc_id)
    bot.run()
