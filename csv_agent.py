"""
AI-агент для анализа CSV файлов с использованием Claude Sonnet 4.5 через OpenRouter
Аналог Julius.ai
"""

import os
import sys
import io
import json
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import contextlib

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Для работы без GUI
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI


class CSVAnalysisAgent:
    """
    AI-агент для анализа CSV файлов.
    Использует Claude Sonnet 4.5 через OpenRouter API.
    """

    def __init__(self, api_key: str, working_dir: str = "."):
        """
        Инициализация агента

        Args:
            api_key: API ключ для OpenRouter
            working_dir: Рабочая директория для поиска CSV файлов
        """
        self.api_key = api_key
        self.working_dir = Path(working_dir)

        # Инициализация клиента OpenRouter (совместим с OpenAI API)
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )

        self.model = "anthropic/claude-sonnet-4.5"
        self.current_csv = None
        self.current_df = None
        self.conversation_history = []
        self.max_retries = 3  # Максимум попыток исправления ошибок

        # Настройки для графиков
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['figure.dpi'] = 100

    def find_csv_files(self) -> List[Path]:
        """Найти все CSV файлы в рабочей директории"""
        csv_files = list(self.working_dir.glob("*.csv"))
        return csv_files

    def load_csv(self, file_path: Path) -> pd.DataFrame:
        """
        Загрузить CSV файл

        Args:
            file_path: Путь к CSV файлу

        Returns:
            DataFrame с данными
        """
        try:
            df = pd.read_csv(file_path)
            self.current_csv = file_path
            self.current_df = df
            return df
        except Exception as e:
            raise Exception(f"Ошибка при загрузке CSV файла: {str(e)}")

    def analyze_csv_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Анализ схемы CSV файла

        Args:
            df: DataFrame для анализа

        Returns:
            Словарь с информацией о схеме
        """
        schema = {
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "shape": df.shape,
            "missing_values": df.isnull().sum().to_dict(),
            "sample_data": df.head(5).to_dict(orient='records'),
            "summary_stats": {}
        }

        # Статистика для числовых колонок
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            schema["summary_stats"] = df[numeric_cols].describe().to_dict()

        return schema

    def execute_python_code(self, code: str, df: pd.DataFrame) -> Tuple[bool, Any, str]:
        """
        Безопасное выполнение Python кода

        Args:
            code: Python код для выполнения
            df: DataFrame для работы

        Returns:
            Кортеж (успех, результат, вывод/ошибка)
        """
        # Создаем изолированное окружение для выполнения
        local_vars = {
            'df': df.copy(),
            'pd': pd,
            'np': np,
            'plt': plt,
            'sns': sns,
            'result': None
        }

        # Перехватываем stdout и stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):

                # Выполняем код
                exec(code, local_vars)

                # Получаем результат
                result = local_vars.get('result', None)
                output = stdout_capture.getvalue()

                # Если результат - это matplotlib figure, сохраняем его
                if plt.get_fignums():
                    output_dir = self.working_dir / "outputs"
                    output_dir.mkdir(exist_ok=True)

                    for i, fig_num in enumerate(plt.get_fignums()):
                        fig = plt.figure(fig_num)
                        fig_path = output_dir / f"plot_{fig_num}.png"
                        fig.savefig(fig_path, bbox_inches='tight', dpi=150)
                        output += f"\n[График сохранен: {fig_path}]"

                    plt.close('all')

                return True, result, output

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return False, None, error_msg
        finally:
            plt.close('all')

    def generate_code_with_retry(self, user_query: str, schema: Dict,
                                 previous_error: Optional[str] = None) -> str:
        """
        Генерация Python кода с помощью Claude

        Args:
            user_query: Запрос пользователя
            schema: Схема данных CSV
            previous_error: Предыдущая ошибка (для повторной попытки)

        Returns:
            Сгенерированный Python код
        """
        # Формируем промпт для Claude
        system_prompt = """Ты - эксперт по анализу данных на Python.
Твоя задача - писать качественный Python код для анализа CSV данных.

Правила:
1. Используй только библиотеки: pandas, numpy, matplotlib, seaborn
2. DataFrame доступен как переменная 'df'
3. Если нужно вернуть результат, сохрани его в переменную 'result'
4. Для визуализации используй matplotlib/seaborn
5. Код должен быть безопасным и эффективным
6. Всегда проверяй существование колонок перед использованием
7. Обрабатывай возможные ошибки (NaN, типы данных и т.д.)
8. Возвращай ТОЛЬКО код Python, без объяснений и markdown разметки
9. Не используй print() если не требуется явный вывод
"""

        user_message = f"""
Данные CSV файла:
- Колонки: {schema['columns']}
- Типы данных: {schema['dtypes']}
- Размер: {schema['shape'][0]} строк, {schema['shape'][1]} колонок
- Пропущенные значения: {schema['missing_values']}
- Примеры данных (первые 5 строк):
{json.dumps(schema['sample_data'], indent=2, ensure_ascii=False)}

Запрос пользователя: {user_query}
"""

        if previous_error:
            user_message += f"""

ПРЕДЫДУЩАЯ ПОПЫТКА ЗАВЕРШИЛАСЬ ОШИБКОЙ:
{previous_error}

Исправь код, учитывая эту ошибку. Напиши исправленную версию кода.
"""

        # Добавляем в историю
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Отправляем запрос к Claude
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=4000
            )

            code = response.choices[0].message.content.strip()

            # Убираем markdown разметку если есть
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]

            return code.strip()

        except Exception as e:
            raise Exception(f"Ошибка при генерации кода: {str(e)}")

    def analyze_and_execute(self, user_query: str) -> Dict[str, Any]:
        """
        Основной метод: анализ запроса и выполнение кода

        Args:
            user_query: Запрос пользователя

        Returns:
            Словарь с результатами
        """
        if self.current_df is None:
            return {
                "success": False,
                "error": "CSV файл не загружен. Сначала загрузите файл методом load_csv()"
            }

        # Получаем схему данных
        schema = self.analyze_csv_schema(self.current_df)

        result = {
            "success": False,
            "query": user_query,
            "code_attempts": [],
            "final_result": None,
            "output": None,
            "error": None
        }

        # Пробуем выполнить с повторными попытками
        previous_error = None

        for attempt in range(self.max_retries):
            print(f"\n{'='*60}")
            print(f"Попытка {attempt + 1}/{self.max_retries}")
            print(f"{'='*60}")

            # Генерируем код
            try:
                code = self.generate_code_with_retry(user_query, schema, previous_error)
                print(f"\nСгенерированный код:")
                print("-" * 60)
                print(code)
                print("-" * 60)

                result["code_attempts"].append({
                    "attempt": attempt + 1,
                    "code": code
                })

            except Exception as e:
                result["error"] = f"Ошибка генерации кода: {str(e)}"
                break

            # Выполняем код
            success, exec_result, output = self.execute_python_code(code, self.current_df)

            if success:
                print(f"\n✓ Код выполнен успешно!")
                print(f"\nРезультат:")
                print("-" * 60)
                if output:
                    print(output)
                if exec_result is not None:
                    print(f"Возвращаемое значение: {exec_result}")
                print("-" * 60)

                result["success"] = True
                result["final_result"] = exec_result
                result["output"] = output
                result["code_attempts"][-1]["success"] = True
                break
            else:
                print(f"\n✗ Ошибка выполнения:")
                print("-" * 60)
                print(output)
                print("-" * 60)

                previous_error = output
                result["code_attempts"][-1]["success"] = False
                result["code_attempts"][-1]["error"] = output

                if attempt == self.max_retries - 1:
                    result["error"] = f"Не удалось выполнить код после {self.max_retries} попыток"

        # Сохраняем в историю
        self.conversation_history.append({
            "query": user_query,
            "result": result
        })

        return result

    def chat(self, user_query: str) -> str:
        """
        Простой интерфейс чата

        Args:
            user_query: Запрос пользователя

        Returns:
            Текстовый ответ
        """
        result = self.analyze_and_execute(user_query)

        if result["success"]:
            response = f"\n✓ Анализ выполнен успешно!\n"
            if result["output"]:
                response += f"\n{result['output']}\n"
            if result["final_result"] is not None:
                response += f"\nРезультат: {result['final_result']}\n"
            return response
        else:
            return f"\n✗ Ошибка: {result.get('error', 'Неизвестная ошибка')}\n"


def main():
    """Основная функция для запуска агента"""
    from dotenv import load_dotenv

    # Загружаем переменные окружения
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Ошибка: Установите переменную окружения OPENROUTER_API_KEY")
        sys.exit(1)

    # Создаем агента
    print("="*60)
    print("AI CSV Analysis Agent")
    print("Powered by Claude Sonnet 4.5")
    print("="*60)

    agent = CSVAnalysisAgent(api_key)

    # Ищем CSV файлы
    csv_files = agent.find_csv_files()

    if not csv_files:
        print("\nОшибка: CSV файлы не найдены в текущей директории")
        print("Поместите CSV файл в директорию с программой и попробуйте снова")
        sys.exit(1)

    # Если файлов несколько, даем выбрать
    if len(csv_files) == 1:
        selected_file = csv_files[0]
    else:
        print(f"\nНайдено {len(csv_files)} CSV файлов:")
        for i, f in enumerate(csv_files, 1):
            print(f"{i}. {f.name}")

        while True:
            try:
                choice = int(input("\nВыберите номер файла: "))
                if 1 <= choice <= len(csv_files):
                    selected_file = csv_files[choice - 1]
                    break
                else:
                    print("Неверный номер, попробуйте снова")
            except ValueError:
                print("Введите число")

    # Загружаем CSV
    print(f"\nЗагрузка файла: {selected_file.name}")
    try:
        df = agent.load_csv(selected_file)
        print(f"✓ Файл загружен: {df.shape[0]} строк, {df.shape[1]} колонок")
        print(f"Колонки: {', '.join(df.columns)}")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    # Интерактивный чат
    print("\n" + "="*60)
    print("Чат запущен! Задавайте вопросы о данных.")
    print("Команды: 'exit' - выход, 'schema' - показать структуру данных")
    print("="*60 + "\n")

    while True:
        try:
            user_input = input("\nВаш вопрос: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'выход']:
                print("До свидания!")
                break

            if user_input.lower() == 'schema':
                schema = agent.analyze_csv_schema(agent.current_df)
                print(f"\nСтруктура данных:")
                print(f"Колонки: {schema['columns']}")
                print(f"Типы: {schema['dtypes']}")
                print(f"Размер: {schema['shape']}")
                continue

            # Выполняем анализ
            response = agent.chat(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\n\nПрервано пользователем. До свидания!")
            break
        except Exception as e:
            print(f"\nОшибка: {e}")


if __name__ == "__main__":
    main()
