from hanyu_recap_sheet import HanyuRecapSheet  # ← 네 파일 이름에 맞게 수정!

def main_menu():
    print("\n🎯 원하는 작업을 선택하세요:")
    print("1. 기존 문서 정리 (Google Docs → Sheets)")
    print("2. 병음만 다시 생성")
    print("3. 랜덤 복습 (모든 문장)")
    print("4. 랜덤 복습 (시트별 3개씩)")
    print("5. 특정 시트에서 복습 생성 (랜덤 셔플)")
    print("6. 종료")
    return input("입력 (1~6): ").strip()

def main():
    while True:
        choice = main_menu()

        if choice == "1":
            doc_id = input("문서 ID가 있다면 입력하세요 (없으면 Enter): ").strip()
            bot = HanyuRecapSheet(doc_id=doc_id or None)
            bot.run()

        elif choice == "2":
            sheet_id = input("시트 ID를 입력하세요: ").strip()
            bot = HanyuRecapSheet()
            bot.regenerate_pinyin_only(sheet_id)

        elif choice == "3":
            bot = HanyuRecapSheet()
            bot.create_review_sheet_from_drive(mode="all")

        elif choice == "4":
            bot = HanyuRecapSheet()
            bot.create_review_sheet_from_drive(mode="count", per_sheet=3)

        elif choice == "5":
            spreadsheet_id = input("📄 복습 대상 Spreadsheet ID를 입력하세요: ").strip()
            count_input = input("몇 개 문장을 가져올까요? (Enter 시 전체): ").strip()
            sample_count = int(count_input) if count_input else None
            bot = HanyuRecapSheet()
            bot.create_review_from_sheet(spreadsheet_id=spreadsheet_id, sample_count=sample_count)

        elif choice == "6":
            print("👋 종료합니다!")
            break

        else:
            print("❌ 잘못된 입력입니다. 다시 선택해주세요.")

if __name__ == "__main__":
    main()
