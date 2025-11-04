"""
Тестовий скрипт для перевірки аналізу фільтрів
"""
from ai.agent import claude_agent

print("=" * 60)
print("ТЕСТ АНАЛІЗУ ФІЛЬТРІВ")
print("=" * 60)

test_cases = [
    {
        "name": "Повна інформація",
        "filters": {
            "name": "Данило",
            "type": "квартира",
            "district": "Приморський",
            "rooms": 3,
            "state": "з ремонтом",
            "budget": 20000000
        },
        "expected": [1, 2, 3, 4, 5, 6]
    },
    {
        "name": "Тільки кімнати і бюджет",
        "filters": {
            "rooms": 3,
            "budget": 20000000
        },
        "expected": [4, 6]
    },
    {
        "name": "Тільки тип",
        "filters": {
            "type": "квартира"
        },
        "expected": [2]
    },
    {
        "name": "Порожньо",
        "filters": {},
        "expected": []
    }
]

for test in test_cases:
    result = claude_agent._analyze_filters(test["filters"])
    status = "✅" if result == test["expected"] else "❌"
    print(f"\n{status} {test['name']}")
    print(f"   Фільтри: {test['filters']}")
    print(f"   Очікувалось: {test['expected']}")
    print(f"   Отримано: {result}")

print("\n" + "=" * 60)
print("ТЕСТ ЗАВЕРШЕНО")
print("=" * 60)
