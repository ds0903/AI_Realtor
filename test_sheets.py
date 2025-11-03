"""
Тестовий скрипт для перевірки читання з Google Sheets
"""
from services.google_sheets import sheets_service

print("=" * 60)
print("ТЕСТ GOOGLE SHEETS")
print("=" * 60)

try:
    print("\nWELCOME:")
    welcome = sheets_service.get_welcome_messages()
    for i, msg in enumerate(welcome, 1):
        print(f"  {i}. {msg}")
    
    print("\nQUESTIONS:")
    questions = sheets_service.get_questions()
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")
    
    print("\nOBJECTIONS:")
    objections = sheets_service.get_objections()
    for i, obj in enumerate(objections, 1):
        print(f"  {i}. {obj}")
    
    print("\nREACTIONS:")
    reactions = sheets_service.get_reactions()
    for i, r in enumerate(reactions, 1):
        print(f"  {i}. {r}")
    
    print("\n" + "=" * 60)
    print("СТАТИСТИКА:")
    print(f"  Привітання: {len(welcome)}")
    print(f"  Питання: {len(questions)}")
    print(f"  Заперечення: {len(objections)}")
    print(f"  Реакції: {len(reactions)}")
    
    if len(questions) != 6:
        print(f"\n⚠️  МАЄ БУТИ 6 ПИТАНЬ, А Є {len(questions)}!")
    else:
        print("\n✅ ВСЕ ОК - 6 ПИТАНЬ!")
    
except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
