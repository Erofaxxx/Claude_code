#!/usr/bin/env python3
"""
Скрипт для проверки валидности OpenRouter API ключа
Используйте этот скрипт для диагностики проблем с аутентификацией
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Загружаем переменные окружения
load_dotenv()

print("=" * 60)
print("OpenRouter API Key Test")
print("=" * 60)
print()

# Получаем API ключ
api_key = os.getenv("OPENROUTER_API_KEY")

# Проверка 1: Наличие ключа
print("1. Проверка наличия API ключа...")
if not api_key:
    print("❌ ОШИБКА: OPENROUTER_API_KEY не найден в переменных окружения")
    print()
    print("Решение:")
    print("  1. Создайте файл .env в корне проекта")
    print("  2. Добавьте строку: OPENROUTER_API_KEY=sk-or-v1-ваш-ключ")
    print("  3. Получите ключ на: https://openrouter.ai/keys")
    print()
    sys.exit(1)

print(f"✓ API ключ найден")
print()

# Проверка 2: Формат ключа
print("2. Проверка формата ключа...")
api_key = api_key.strip()  # Убираем пробелы

print(f"   Длина ключа: {len(api_key)} символов")
print(f"   Начало ключа: {api_key[:15]}...")
print(f"   Конец ключа: ...{api_key[-10:]}")
print()

if not api_key.startswith("sk-"):
    print("⚠️  ПРЕДУПРЕЖДЕНИЕ: Ключ не начинается с 'sk-'")
    print("   OpenRouter ключи обычно имеют формат: sk-or-v1-...")
    print()
else:
    print("✓ Формат ключа корректный (начинается с 'sk-')")
    print()

# Проверка 3: Тест реального API запроса
print("3. Тестовый запрос к OpenRouter API...")
print("   Отправляем простой запрос к Claude Sonnet 4.5...")
print()

try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4.5",
        messages=[
            {"role": "user", "content": "Ответь одним словом: привет"}
        ],
        max_tokens=10
    )

    result = response.choices[0].message.content

    print("✓ API запрос успешен!")
    print(f"   Ответ от Claude: {result}")
    print()
    print("=" * 60)
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
    print("=" * 60)
    print()
    print("Ваш API ключ работает корректно.")
    print("Если сервер все еще выдает ошибку 401, проверьте:")
    print("  - Перезапустили ли вы сервер после изменения .env")
    print("  - Использует ли сервер тот же .env файл")
    print()

except Exception as e:
    error_str = str(e)
    print("❌ ОШИБКА при запросе к API:")
    print(f"   {error_str}")
    print()

    # Анализ ошибок
    if "401" in error_str or "Unauthorized" in error_str or "User not found" in error_str:
        print("Диагностика: Ошибка аутентификации (401)")
        print()
        print("Возможные причины:")
        print("  1. API ключ неверный или истек")
        print("  2. API ключ не активирован на OpenRouter")
        print("  3. У ключа нет доступа к модели claude-sonnet-4.5")
        print()
        print("Решение:")
        print("  1. Проверьте ключ на https://openrouter.ai/keys")
        print("  2. Убедитесь что у вас есть кредиты на аккаунте")
        print("  3. Создайте новый ключ если текущий не работает")
        print("  4. Проверьте что ключ скопирован полностью (без пробелов)")

    elif "403" in error_str or "Forbidden" in error_str:
        print("Диагностика: Доступ запрещен (403)")
        print()
        print("Возможные причины:")
        print("  1. У API ключа нет доступа к этой модели")
        print("  2. Недостаточно кредитов на аккаунте")
        print()

    elif "429" in error_str or "rate limit" in error_str.lower():
        print("Диагностика: Превышен лимит запросов (429)")
        print()
        print("Подождите немного и попробуйте снова.")

    else:
        print("Диагностика: Неизвестная ошибка")
        print()
        print("Проверьте:")
        print("  1. Подключение к интернету")
        print("  2. Доступность openrouter.ai")
        print("  3. Логи сервера для подробностей")

    print()
    sys.exit(1)
