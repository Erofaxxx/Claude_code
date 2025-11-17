"""
Скрипт для тестирования API сервера
"""

import requests
import json
import sys
from pathlib import Path


def test_health_check(base_url):
    """Тест health check endpoint"""
    print("\n" + "="*60)
    print("Тест 1: Health Check")
    print("="*60)

    try:
        response = requests.get(f"{base_url}/health")
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        if response.status_code == 200:
            print("✓ Health check успешен")
            return True
        else:
            print("✗ Health check не прошел")
            return False
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def test_schema_endpoint(base_url, csv_file):
    """Тест получения схемы CSV"""
    print("\n" + "="*60)
    print("Тест 2: Получение схемы CSV")
    print("="*60)

    try:
        with open(csv_file, 'rb') as f:
            files = {'file': (csv_file.name, f, 'text/csv')}
            response = requests.post(f"{base_url}/api/schema", files=files)

        print(f"Статус: {response.status_code}")
        result = response.json()

        if response.status_code == 200 and result.get('success'):
            print("✓ Схема получена успешно")
            print(f"Колонки: {result['schema']['columns']}")
            print(f"Размер: {result['schema']['shape']}")
            return True
        else:
            print(f"✗ Ошибка: {result}")
            return False
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def test_analyze_endpoint(base_url, csv_file, query):
    """Тест анализа CSV"""
    print("\n" + "="*60)
    print(f"Тест 3: Анализ данных")
    print(f"Запрос: {query}")
    print("="*60)

    try:
        with open(csv_file, 'rb') as f:
            files = {'file': (csv_file.name, f, 'text/csv')}
            data = {'query': query}
            response = requests.post(
                f"{base_url}/api/analyze",
                files=files,
                data=data,
                timeout=120  # 2 минуты таймаут
            )

        print(f"Статус: {response.status_code}")
        result = response.json()

        if result.get('success'):
            print("✓ Анализ выполнен успешно")
            print(f"\nПопыток: {result['attempts_count']}")

            if result.get('final_code'):
                print(f"\nСгенерированный код:")
                print("-" * 60)
                print(result['final_code'])
                print("-" * 60)

            if result.get('text_output'):
                print(f"\nВывод:")
                print(result['text_output'])

            if result.get('result_data'):
                print(f"\nДанные результата:")
                print(json.dumps(result['result_data'], indent=2, ensure_ascii=False)[:500])

            if result.get('plots'):
                print(f"\nГрафиков создано: {len(result['plots'])}")
                for i, plot in enumerate(result['plots'], 1):
                    print(f"  - График {i}: {len(plot)} символов base64")

            return True
        else:
            print(f"✗ Ошибка анализа: {result.get('error')}")
            if result.get('error_details'):
                print(f"\nДетали ошибки:")
                print(result['error_details'][:500])
            return False

    except requests.Timeout:
        print("✗ Превышено время ожидания (timeout)")
        return False
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def test_analyze_with_history(base_url, csv_file):
    """Тест анализа с историей диалога"""
    print("\n" + "="*60)
    print("Тест 4: Анализ с историей диалога")
    print("="*60)

    # Первый запрос
    query1 = "Какая средняя цена?"
    print(f"\nЗапрос 1: {query1}")

    with open(csv_file, 'rb') as f:
        files = {'file': (csv_file.name, f, 'text/csv')}
        data = {'query': query1}
        response1 = requests.post(
            f"{base_url}/api/analyze",
            files=files,
            data=data,
            timeout=120
        )

    result1 = response1.json()

    if not result1.get('success'):
        print("✗ Первый запрос не выполнен")
        return False

    print("✓ Первый запрос выполнен")

    # Второй запрос с историей
    query2 = "Теперь построй график цен"
    print(f"\nЗапрос 2: {query2}")

    history = [{
        "query": query1,
        "success": result1['success'],
        "text_output": result1.get('text_output', ''),
        "result_data": result1.get('result_data')
    }]

    with open(csv_file, 'rb') as f:
        files = {'file': (csv_file.name, f, 'text/csv')}
        data = {
            'query': query2,
            'chat_history': json.dumps(history)
        }
        response2 = requests.post(
            f"{base_url}/api/analyze",
            files=files,
            data=data,
            timeout=120
        )

    result2 = response2.json()

    if result2.get('success'):
        print("✓ Запрос с историей выполнен успешно")
        if result2.get('plots'):
            print(f"  Создано графиков: {len(result2['plots'])}")
        return True
    else:
        print(f"✗ Ошибка: {result2.get('error')}")
        return False


def main():
    """Основная функция тестирования"""
    print("""
╔════════════════════════════════════════════════════════════╗
║         CSV Analysis Agent API - Тестирование              ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Настройки
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = input("Введите URL API (по умолчанию http://localhost:8000): ").strip()
        if not base_url:
            base_url = "http://localhost:8000"

    # Проверка наличия тестового файла
    csv_file = Path("example_sales.csv")
    if not csv_file.exists():
        print(f"✗ Файл {csv_file} не найден!")
        print("  Создайте тестовый CSV файл или укажите другой путь.")
        return

    print(f"\nURL API: {base_url}")
    print(f"Тестовый файл: {csv_file}")

    # Запуск тестов
    results = []

    results.append(("Health Check", test_health_check(base_url)))
    results.append(("Schema Endpoint", test_schema_endpoint(base_url, csv_file)))
    results.append(("Analyze Endpoint", test_analyze_endpoint(
        base_url,
        csv_file,
        "Покажи описательную статистику по цене"
    )))
    results.append(("Analyze with History", test_analyze_with_history(base_url, csv_file)))

    # Итоги
    print("\n" + "="*60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:.<40} {status}")

    total = len(results)
    passed = sum(1 for _, success in results if success)

    print(f"\nВсего тестов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Провалено: {total - passed}")

    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("\n⚠️  Некоторые тесты не прошли. Проверьте логи сервера.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
