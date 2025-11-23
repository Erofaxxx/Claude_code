#!/usr/bin/env python3
"""
Скрипт для тестирования разных AI моделей
Демонстрирует как использовать различные модели для анализа CSV
"""

import os
import sys
import requests
from pathlib import Path

# URL сервера
API_URL = os.getenv("API_URL", "http://localhost:8000")

def get_available_models():
    """Получить список доступных моделей"""
    print("=" * 60)
    print("Получение списка доступных AI моделей...")
    print("=" * 60)

    response = requests.get(f"{API_URL}/api/models")

    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Найдено {len(data['models'])} моделей\n")

        print("Доступные модели:\n")
        for i, model in enumerate(data['models'], 1):
            star = "⭐" if model['recommended'] else "  "
            default = "(по умолчанию)" if model['is_default'] else ""

            print(f"{i}. {star} {model['name']} {default}")
            print(f"   Ключ: {model['key']}")
            print(f"   Провайдер: {model['provider']}")
            print(f"   Описание: {model['description']}")
            print(f"   Контекст: {model['context_length']:,} токенов")
            print()

        return data['models']
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)
        return []


def test_model_with_query(csv_file_path: str, model_key: str, query: str):
    """
    Тестирует конкретную модель с запросом

    Args:
        csv_file_path: Путь к CSV файлу
        model_key: Ключ модели (например: "gpt-4o", "claude-sonnet-4.5")
        query: Запрос для анализа
    """
    print("\n" + "=" * 60)
    print(f"Тестирование модели: {model_key}")
    print(f"Запрос: {query}")
    print("=" * 60)

    if not Path(csv_file_path).exists():
        print(f"❌ Файл не найден: {csv_file_path}")
        return

    try:
        # Подготовка данных
        files = {
            'file': open(csv_file_path, 'rb')
        }
        data = {
            'query': query,
            'model': model_key
        }

        # Отправка запроса
        print(f"\n📤 Отправка запроса к {API_URL}/api/quick-analyze...")
        response = requests.post(
            f"{API_URL}/api/quick-analyze",
            files=files,
            data=data,
            timeout=60
        )

        files['file'].close()

        if response.status_code == 200:
            result = response.json()

            print("\n✅ Анализ выполнен успешно!")
            print(f"\nМодель: {result.get('model_info', {}).get('model_name', 'Unknown')}")
            print(f"Провайдер: {result.get('model_info', {}).get('provider', 'Unknown')}")
            print(f"Попыток: {result.get('attempts_count', 0)}")

            if result.get('success'):
                print("\n📊 Результат:")
                print("-" * 60)

                # Текстовый вывод (логи)
                if result.get('text_output'):
                    print("\nЛоги выполнения:")
                    print(result['text_output'])

                # Результат анализа (Markdown)
                if result.get('result_data'):
                    print("\n📄 Результат анализа:")
                    print(result['result_data'])

                # Графики
                if result.get('plots'):
                    print(f"\n📈 Создано графиков: {len(result['plots'])}")

            else:
                print(f"\n❌ Ошибка: {result.get('error', 'Unknown error')}")
                if result.get('error_details'):
                    print(f"Детали: {result['error_details']}")

        else:
            print(f"\n❌ HTTP ошибка: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"\n❌ Исключение: {str(e)}")


def compare_models(csv_file_path: str, query: str, models: list):
    """
    Сравнивает несколько моделей на одном запросе

    Args:
        csv_file_path: Путь к CSV файлу
        query: Запрос для анализа
        models: Список ключей моделей для сравнения
    """
    print("\n" + "=" * 60)
    print("СРАВНЕНИЕ МОДЕЛЕЙ")
    print("=" * 60)
    print(f"Файл: {csv_file_path}")
    print(f"Запрос: {query}")
    print(f"Модели: {', '.join(models)}")
    print()

    results = {}

    for model_key in models:
        print(f"\n🔄 Тестирую модель: {model_key}...")
        test_model_with_query(csv_file_path, model_key, query)
        results[model_key] = "✓"

    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ СРАВНЕНИЯ")
    print("=" * 60)
    for model_key, status in results.items():
        print(f"{status} {model_key}")


def interactive_mode():
    """Интерактивный режим выбора модели"""
    print("\n" + "=" * 60)
    print("ИНТЕРАКТИВНЫЙ РЕЖИМ")
    print("=" * 60)

    # Получаем модели
    models = get_available_models()
    if not models:
        print("Не удалось получить список моделей")
        return

    # Выбор модели
    print("\nВыберите модель (введите номер или ключ):")
    choice = input("> ").strip()

    selected_model = None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            selected_model = models[idx]['key']
    else:
        # Поиск по ключу
        for model in models:
            if model['key'] == choice:
                selected_model = choice
                break

    if not selected_model:
        print("❌ Неверный выбор")
        return

    print(f"\n✓ Выбрана модель: {selected_model}")

    # Путь к CSV
    print("\nВведите путь к CSV файлу:")
    csv_path = input("> ").strip()

    if not Path(csv_path).exists():
        print(f"❌ Файл не найден: {csv_path}")
        return

    # Запрос
    print("\nВведите запрос для анализа:")
    query = input("> ").strip()

    if not query:
        print("❌ Запрос не может быть пустым")
        return

    # Выполняем анализ
    test_model_with_query(csv_path, selected_model, query)


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("""
Использование:
  python test_models.py list                                    - Список моделей
  python test_models.py test <csv> <model> <query>              - Тест одной модели
  python test_models.py compare <csv> <query> <model1> <model2> - Сравнение моделей
  python test_models.py interactive                             - Интерактивный режим

Примеры:
  python test_models.py list
  python test_models.py test finance.csv gpt-4o "Выведи топ-5 статей расходов"
  python test_models.py compare sales.csv "Построй график" claude-sonnet-4.5 gpt-4o
  python test_models.py interactive
        """)
        return

    command = sys.argv[1]

    if command == "list":
        get_available_models()

    elif command == "test":
        if len(sys.argv) < 5:
            print("❌ Недостаточно аргументов для test")
            print("Использование: python test_models.py test <csv> <model> <query>")
            return

        csv_file = sys.argv[2]
        model_key = sys.argv[3]
        query = sys.argv[4]

        test_model_with_query(csv_file, model_key, query)

    elif command == "compare":
        if len(sys.argv) < 5:
            print("❌ Недостаточно аргументов для compare")
            print("Использование: python test_models.py compare <csv> <query> <model1> <model2> ...")
            return

        csv_file = sys.argv[2]
        query = sys.argv[3]
        models = sys.argv[4:]

        compare_models(csv_file, query, models)

    elif command == "interactive":
        interactive_mode()

    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Используйте: list, test, compare или interactive")


if __name__ == "__main__":
    main()
