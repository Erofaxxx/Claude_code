"""
Примеры использования AI CSV Analysis Agent
"""

from csv_agent import CSVAnalysisAgent
from pathlib import Path
import os

def example_basic_usage():
    """Базовое использование агента"""
    print("=" * 60)
    print("Пример 1: Базовое использование")
    print("=" * 60)

    # Создание агента
    api_key = os.getenv("OPENROUTER_API_KEY", "your_api_key_here")
    agent = CSVAnalysisAgent(api_key)

    # Загрузка CSV
    csv_path = Path("example_sales.csv")
    if not csv_path.exists():
        print(f"Ошибка: файл {csv_path} не найден")
        return

    df = agent.load_csv(csv_path)
    print(f"\n✓ Загружено: {df.shape[0]} строк, {df.shape[1]} колонок\n")

    # Простой анализ
    print("\n" + "=" * 60)
    print("Запрос 1: Описательная статистика")
    print("=" * 60)
    response = agent.chat("Покажи описательную статистику по всем числовым колонкам")
    print(response)

    print("\n" + "=" * 60)
    print("Запрос 2: Визуализация")
    print("=" * 60)
    response = agent.chat("Построй гистограмму распределения цен")
    print(response)


def example_detailed_analysis():
    """Детальный анализ с использованием методов агента"""
    print("\n" + "=" * 60)
    print("Пример 2: Детальный анализ")
    print("=" * 60)

    api_key = os.getenv("OPENROUTER_API_KEY", "your_api_key_here")
    agent = CSVAnalysisAgent(api_key)

    csv_path = Path("example_sales.csv")
    if not csv_path.exists():
        print(f"Ошибка: файл {csv_path} не найден")
        return

    df = agent.load_csv(csv_path)

    # Анализ схемы
    schema = agent.analyze_csv_schema(df)
    print("\nСхема данных:")
    print(f"Колонки: {schema['columns']}")
    print(f"Типы: {schema['dtypes']}")
    print(f"Размер: {schema['shape']}")
    print(f"Пропущенные значения: {schema['missing_values']}")

    # Выполнение анализа
    print("\n" + "=" * 60)
    print("Выполнение анализа")
    print("=" * 60)

    result = agent.analyze_and_execute(
        "Найди топ-5 продуктов по общему объему продаж и построй bar chart"
    )

    if result["success"]:
        print("\n✓ Анализ выполнен успешно!")
        print(f"Попыток: {len(result['code_attempts'])}")
        print(f"\nИспользованный код:")
        print("-" * 60)
        print(result['code_attempts'][-1]['code'])
        print("-" * 60)
    else:
        print(f"\n✗ Ошибка: {result['error']}")


def example_multiple_queries():
    """Несколько последовательных запросов"""
    print("\n" + "=" * 60)
    print("Пример 3: Несколько запросов подряд")
    print("=" * 60)

    api_key = os.getenv("OPENROUTER_API_KEY", "your_api_key_here")
    agent = CSVAnalysisAgent(api_key)

    csv_path = Path("example_sales.csv")
    if not csv_path.exists():
        print(f"Ошибка: файл {csv_path} не найден")
        return

    df = agent.load_csv(csv_path)

    queries = [
        "Какая средняя цена продукта?",
        "Сколько всего продаж было совершено?",
        "Построй линейный график продаж по датам",
        "Найди корреляцию между ценой и количеством",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 60}")
        print(f"Запрос {i}: {query}")
        print("=" * 60)

        response = agent.chat(query)
        print(response)


def example_error_recovery():
    """Демонстрация исправления ошибок"""
    print("\n" + "=" * 60)
    print("Пример 4: Автоматическое исправление ошибок")
    print("=" * 60)

    api_key = os.getenv("OPENROUTER_API_KEY", "your_api_key_here")
    agent = CSVAnalysisAgent(api_key)

    csv_path = Path("example_sales.csv")
    if not csv_path.exists():
        print(f"Ошибка: файл {csv_path} не найден")
        return

    df = agent.load_csv(csv_path)

    # Запрос который может вызвать ошибку (несуществующая колонка)
    # Агент должен исправить и адаптировать код
    print("\nЗапрос с потенциальной ошибкой:")
    result = agent.analyze_and_execute(
        "Покажи статистику по колонке 'revenue' (если её нет, используй похожую)"
    )

    print(f"\nПопыток выполнения: {len(result['code_attempts'])}")
    for i, attempt in enumerate(result['code_attempts'], 1):
        print(f"\nПопытка {i}:")
        print(f"Успех: {attempt.get('success', False)}")
        if not attempt.get('success'):
            print(f"Ошибка: {attempt.get('error', 'N/A')[:100]}...")


def example_custom_code():
    """Пример с кастомным кодом"""
    print("\n" + "=" * 60)
    print("Пример 5: Выполнение кастомного кода")
    print("=" * 60)

    api_key = os.getenv("OPENROUTER_API_KEY", "your_api_key_here")
    agent = CSVAnalysisAgent(api_key)

    csv_path = Path("example_sales.csv")
    if not csv_path.exists():
        print(f"Ошибка: файл {csv_path} не найден")
        return

    df = agent.load_csv(csv_path)

    # Прямое выполнение кода
    custom_code = """
# Анализ продаж
total_sales = df['quantity'].sum()
avg_price = df['price'].mean()

result = {
    'total_sales': total_sales,
    'average_price': avg_price,
    'total_revenue': (df['quantity'] * df['price']).sum()
}

print(f"Всего продаж: {total_sales}")
print(f"Средняя цена: ${avg_price:.2f}")
print(f"Общая выручка: ${result['total_revenue']:.2f}")
"""

    print("Выполнение кастомного кода:")
    print("-" * 60)
    print(custom_code)
    print("-" * 60)

    success, result, output = agent.execute_python_code(custom_code, df)

    if success:
        print("\n✓ Успешно выполнено!")
        print(f"\nВывод:\n{output}")
        print(f"\nРезультат: {result}")
    else:
        print(f"\n✗ Ошибка:\n{output}")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║         AI CSV Analysis Agent - Примеры использования       ║
    ║                 Powered by Claude Sonnet 4.5               ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    # Проверяем наличие API ключа
    if not os.getenv("OPENROUTER_API_KEY"):
        print("\n⚠️  ВНИМАНИЕ: Установите переменную окружения OPENROUTER_API_KEY")
        print("   export OPENROUTER_API_KEY='ваш_ключ'")
        print("   или создайте файл .env\n")

    # Запускаем примеры
    try:
        example_basic_usage()
        example_detailed_analysis()
        example_multiple_queries()
        example_error_recovery()
        example_custom_code()

        print("\n" + "=" * 60)
        print("Все примеры выполнены!")
        print("=" * 60)

    except Exception as e:
        print(f"\nОшибка при выполнении примеров: {e}")
        import traceback
        traceback.print_exc()
