from hanyu_recap_sheet import HanyuRecapSheet

def main_menu():
    print("\n🎯 원하는 작업을 선택하세요:")
    print("1. 기존 문서 정리 (Google Docs → Sheets)")
    print("2. 병음만 다시 생성")
    print("3. 랜덤 복습 (모든 문장)")
    print("4. 랜덤 복습 (시트별 3개씩)")
    print("5. 종료")
    return input("입력 (1~5): ").strip()

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
            print("👋 종료합니다!")
            break

        else:
            print("❌ 잘못된 입력입니다. 다시 선택해주세요.")

if __name__ == "__main__":
    main()
