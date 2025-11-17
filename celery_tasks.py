"""
Celery задачи для фонового выполнения анализа
"""

import os
from celery_config import celery_app
from csv_agent_api import CSVAnalysisAgentAPI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


@celery_app.task(bind=True, name='analyze_csv_task')
def analyze_csv_task(self, file_bytes: bytes, query: str, chat_history: list = None):
    """
    Фоновая задача для анализа CSV

    Args:
        self: Task instance (для обновления статуса)
        file_bytes: Байты CSV файла
        query: Запрос пользователя
        chat_history: История диалога

    Returns:
        Результат анализа в формате dict
    """
    try:
        # Обновление статуса: начало работы
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Инициализация агента...'}
        )

        # Создание агента
        agent = CSVAnalysisAgentAPI(api_key=OPENROUTER_API_KEY)

        # Обновление статуса: загрузка CSV
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Загрузка CSV файла...'}
        )

        # Загрузка CSV
        df = agent.load_csv_from_bytes(file_bytes, "uploaded.csv")

        # Обновление статуса: анализ схемы
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Анализ структуры данных...'}
        )

        # Получение схемы
        schema = agent.analyze_csv_schema(df)

        # Обновление статуса: генерация кода
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Генерация Python кода с помощью Claude...'}
        )

        # Выполнение анализа с прогрессом
        result = analyze_with_progress(self, agent, query, chat_history)

        return result

    except Exception as e:
        # Обновление статуса: ошибка
        self.update_state(
            state='FAILURE',
            meta={'status': f'Ошибка: {str(e)}'}
        )
        raise


def analyze_with_progress(task, agent, query, chat_history):
    """
    Анализ с обновлением прогресса

    Args:
        task: Celery task instance
        agent: CSVAnalysisAgentAPI instance
        query: Запрос пользователя
        chat_history: История диалога

    Returns:
        Результат анализа
    """
    if agent.current_df is None:
        return {
            "success": False,
            "error": "CSV файл не загружен"
        }

    schema = agent.analyze_csv_schema(agent.current_df)

    result = {
        "success": False,
        "query": query,
        "code_attempts": [],
        "final_code": None,
        "result_data": None,
        "text_output": None,
        "plots": [],
        "error": None,
        "attempts_count": 0
    }

    previous_error = None

    for attempt in range(agent.max_retries):
        result["attempts_count"] = attempt + 1

        # Обновление прогресса
        task.update_state(
            state='PROCESSING',
            meta={
                'status': f'Попытка {attempt + 1}/{agent.max_retries}: Генерация кода...',
                'attempt': attempt + 1,
                'max_attempts': agent.max_retries
            }
        )

        # Генерация кода
        try:
            code = agent.generate_code_with_retry(
                query,
                schema,
                chat_history,
                previous_error
            )

            result["code_attempts"].append({
                "attempt": attempt + 1,
                "code": code,
                "success": False
            })

        except Exception as e:
            result["error"] = f"Ошибка генерации кода: {str(e)}"
            break

        # Обновление прогресса: выполнение
        task.update_state(
            state='PROCESSING',
            meta={
                'status': f'Попытка {attempt + 1}/{agent.max_retries}: Выполнение кода...',
                'attempt': attempt + 1,
                'max_attempts': agent.max_retries,
                'code': code
            }
        )

        # Выполнение кода
        success, exec_result, output, plot_base64_list = agent.execute_python_code(
            code, agent.current_df
        )

        if success:
            result["success"] = True
            result["final_code"] = code
            result["result_data"] = exec_result
            result["text_output"] = output
            result["plots"] = plot_base64_list
            result["code_attempts"][-1]["success"] = True

            # Финальный статус
            task.update_state(
                state='SUCCESS',
                meta={
                    'status': 'Анализ завершен успешно!',
                    'result': result
                }
            )
            break
        else:
            previous_error = output
            result["code_attempts"][-1]["error"] = output

            if attempt == agent.max_retries - 1:
                result["error"] = f"Не удалось выполнить код после {agent.max_retries} попыток"
                result["error_details"] = output

    return result


@celery_app.task(name='get_schema_task')
def get_schema_task(file_bytes: bytes):
    """
    Фоновая задача для получения схемы CSV

    Args:
        file_bytes: Байты CSV файла

    Returns:
        Информация о схеме
    """
    try:
        agent = CSVAnalysisAgentAPI(api_key=OPENROUTER_API_KEY)
        df = agent.load_csv_from_bytes(file_bytes, "uploaded.csv")
        schema = agent.analyze_csv_schema(df)

        return {
            "success": True,
            "schema": schema
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
