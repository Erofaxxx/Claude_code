"""
Скрипт для тестирования расширенной версии API
"""

import requests
import json
import time
import sys
from pathlib import Path


def test_health_advanced(base_url):
    """Тест health check с проверкой сервисов"""
    print("\n" + "="*60)
    print("Тест 1: Health Check (Advanced)")
    print("="*60)

    try:
        response = requests.get(f"{base_url}/health")
        print(f"Статус: {response.status_code}")
        result = response.json()

        print(f"Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if response.status_code == 200:
            print("✓ Health check успешен")

            # Проверка сервисов
            services = result.get('services', {})
            if services.get('redis') == 'ok':
                print("  ✓ Redis подключен")
            else:
                print(f"  ✗ Redis: {services.get('redis')}")

            if services.get('celery') == 'ok':
                print("  ✓ Celery работает")
            else:
                print(f"  ✗ Celery: {services.get('celery')}")

            return True
        else:
            print("✗ Health check не прошел")
            return False

    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def test_session_management(base_url):
    """Тест управления сессиями"""
    print("\n" + "="*60)
    print("Тест 2: Управление сессиями")
    print("="*60)

    try:
        # Создание сессии
        print("\nСоздание сессии...")
        response = requests.post(f"{base_url}/api/sessions")
        result = response.json()

        if result.get('success'):
            session_id = result['session_id']
            print(f"✓ Сессия создана: {session_id}")
            print(f"  Истекает через: {result['expires_in']} сек")

            # Получение сессии
            print(f"\nПолучение информации о сессии...")
            response = requests.get(f"{base_url}/api/sessions/{session_id}")
            result = response.json()

            if result.get('success'):
                print(f"✓ Информация получена")
                session_info = result['session']
                print(f"  User ID: {session_info.get('user_id')}")
                print(f"  Создана: {session_info.get('created_at')}")

                # Удаление сессии
                print(f"\nУдаление сессии...")
                response = requests.delete(f"{base_url}/api/sessions/{session_id}")
                result = response.json()

                if result.get('success'):
                    print(f"✓ Сессия удалена")
                    return True

        return False

    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def test_async_analyze(base_url, csv_file, query):
    """Тест асинхронного анализа через Celery"""
    print("\n" + "="*60)
    print("Тест 3: Асинхронный анализ (Celery)")
    print(f"Запрос: {query}")
    print("="*60)

    try:
        # Создание сессии
        print("\n1. Создание сессии...")
        session_response = requests.post(f"{base_url}/api/sessions")
        session_id = session_response.json()['session_id']
        print(f"✓ Сессия: {session_id}")

        # Отправка задачи
        print("\n2. Отправка задачи в очередь...")
        with open(csv_file, 'rb') as f:
            files = {'file': (csv_file.name, f, 'text/csv')}
            data = {
                'session_id': session_id,
                'query': query
            }
            response = requests.post(
                f"{base_url}/api/analyze-async",
                files=files,
                data=data
            )

        result = response.json()

        if result.get('success'):
            task_id = result['task_id']
            print(f"✓ Задача добавлена: {task_id}")
            print(f"  Статус: {result['status']}")

            # Отслеживание статуса
            print("\n3. Отслеживание выполнения...")
            max_attempts = 60  # 60 секунд максимум
            attempt = 0

            while attempt < max_attempts:
                time.sleep(1)
                attempt += 1

                status_response = requests.get(
                    f"{base_url}/api/tasks/{task_id}"
                )
                status_data = status_response.json()

                status = status_data['status']
                print(f"  [{attempt}s] Статус: {status}", end='')

                if status == 'PENDING':
                    print(" - В очереди...")
                elif status == 'PROCESSING':
                    meta = status_data.get('meta', {})
                    print(f" - {meta.get('status', 'Обработка...')}")
                elif status == 'SUCCESS':
                    print(" - Готово!")
                    result_data = status_data.get('result', {})

                    print("\n4. Результат:")
                    print("-" * 60)

                    if result_data.get('success'):
                        print("✓ Анализ выполнен успешно!")

                        if result_data.get('final_code'):
                            print(f"\nКод ({len(result_data['final_code'])} символов)")

                        if result_data.get('text_output'):
                            print(f"\nВывод: {result_data['text_output'][:200]}")

                        if result_data.get('plots'):
                            print(f"\nГрафиков: {len(result_data['plots'])}")

                        print(f"\nПопыток: {result_data.get('attempts_count')}")
                        print("-" * 60)
                        return True
                    else:
                        print(f"✗ Ошибка: {result_data.get('error')}")
                        return False

                elif status == 'FAILURE':
                    print(f" - Ошибка!")
                    meta = status_data.get('meta', {})
                    print(f"  Детали: {meta}")
                    return False

            print("\n✗ Timeout: задача не завершилась за {max_attempts} секунд")
            return False

        else:
            print(f"✗ Ошибка отправки: {result}")
            return False

    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_demo_info(base_url):
    """Информация о WebSocket демо"""
    print("\n" + "="*60)
    print("Тест 4: WebSocket (Информация)")
    print("="*60)

    print("""
WebSocket тестирование через браузер:

1. Откройте файл: websocket_client_example.html

2. Или запустите HTTP сервер:
   python -m http.server 8080
   Откройте: http://localhost:8080/websocket_client_example.html

3. В браузере:
   - Нажмите "Создать новую сессию"
   - Загрузите CSV файл
   - Введите вопрос
   - Нажмите "Анализировать"
   - Наблюдайте real-time прогресс!

WebSocket URL: {base_url.replace('http', 'ws')}/ws/analyze/{{session_id}}
    """.format(base_url=base_url))

    return True


def main():
    """Основная функция"""
    print("""
╔════════════════════════════════════════════════════════════╗
║    CSV Analysis Agent API (Advanced) - Тестирование        ║
║    Features: WebSocket, Redis, Celery                      ║
╚════════════════════════════════════════════════════════════╝
    """)

    # URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = input("Введите URL API (по умолчанию http://localhost:8000): ").strip()
        if not base_url:
            base_url = "http://localhost:8000"

    # Файл
    csv_file = Path("example_sales.csv")
    if not csv_file.exists():
        print(f"✗ Файл {csv_file} не найден!")
        return 1

    print(f"\nURL API: {base_url}")
    print(f"Тестовый файл: {csv_file}")

    # Запуск тестов
    results = []

    results.append(("Health Check", test_health_advanced(base_url)))
    results.append(("Session Management", test_session_management(base_url)))
    results.append(("Async Analyze", test_async_analyze(
        base_url,
        csv_file,
        "Покажи описательную статистику"
    )))
    results.append(("WebSocket Info", test_websocket_demo_info(base_url)))

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
        print("\n🎉 Все тесты пройдены!")
        print("\nСледующие шаги:")
        print("1. Откройте websocket_client_example.html для WebSocket теста")
        print("2. Откройте http://localhost:5555 для Flower (если запущен)")
        print("3. Интегрируйте с вашим frontend приложением")
        return 0
    else:
        print("\n⚠️  Некоторые тесты не прошли.")
        print("\nПроверьте:")
        print("1. Запущен ли Redis: redis-cli ping")
        print("2. Запущен ли Celery worker")
        print("3. Логи сервера")
        return 1


if __name__ == "__main__":
    sys.exit(main())
