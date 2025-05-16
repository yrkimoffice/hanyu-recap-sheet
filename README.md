# Hanyu Recap Sheet 🧠🇨🇳

중국어 문장 및 단어 학습 자동화 도구입니다.  
Google Docs에 입력한 중국어 문장을 읽어와 Google Sheets에 자동으로 다음 내용을 정리합니다:

- 📄 문장 → 한국어 번역 / 병음 변환 포함
- 🈷️ 단어 → 자동 추출 + 병음 + 한국어 번역 시트 생성

---

## 📦 주요 기능

| 기능 | 설명 |
|------|------|
| ✅ Google Docs 문서 생성 또는 가져오기 | 날짜 기준 문서 자동 생성 or 수동 문서 ID 입력 |
| ✅ 문장 정리 시트 생성 | 번역 + 병음 + 원문 정리 |
| ✅ 단어 추출 시트 생성 | 명사/동사 자동 추출 후 병음/번역 포함 |
| ✅ 자동 열 너비 조정 | 보기 쉽게 셀 너비 자동 확장 |
| ✅ meta.json 저장 | 문서 ID 및 시트 정보 자동 기록 |

---

## 🚀 설치 방법

### 1. 파이썬 환경 준비
```bash
pip install -r requirements.txt
````

### 2. Google API 설정

* [Google Cloud Console](https://console.cloud.google.com)에서 OAuth 클라이언트 생성
* `client_secret.json` 파일을 프로젝트 루트에 저장

### 3. 최초 실행 시 인증 진행

```bash
python3 hanyu_recap_sheet.py
```

### 4. 수동 문서 ID 사용 시

```bash
python3 hanyu_recap_sheet.py --doc-id <Google Docs 문서 ID>
```

---

## 📂 파일 구조

```
hanyu_recap_sheet/
├── hanyu_recap_sheet.py   # 메인 스크립트
├── token.json             # 인증 토큰 (자동 생성)
├── client_secret.json     # Google API 클라이언트 정보
├── meta.json              # 최근 실행 정보 기록
├── requirements.txt       # 의존성 리스트
└── .gitignore
```

---

## 🛑 주의사항

* `token.json`, `client_secret.json`은 외부에 유출되지 않도록 주의하세요.
* `deep-translator`는 내부적으로 Google Translate 웹을 사용합니다 (비상업적 개인용 기준).

---

## 🙌 추천 사용 흐름

1. 하루 문장 학습은 Google Docs에 쓰기
2. 스크립트 실행 → 자동 정리 & 단어 추출
3. Google Sheets에서 복습 or Anki 연동