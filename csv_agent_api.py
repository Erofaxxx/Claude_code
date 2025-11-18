"""
API-версия CSV Analysis Agent для интеграции с внешними сервисами
Поддерживает историю диалога и возвращает результаты в JSON с base64 изображениями
"""

import os
import io
import json
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import contextlib
import base64
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI


class CSVAnalysisAgentAPI:
    """
    API-версия агента для анализа CSV файлов
    Поддерживает историю диалога и возвращает результаты в формате API
    """

    def __init__(self, api_key: str):
        """
        Инициализация агента

        Args:
            api_key: API ключ для OpenRouter
        """
        self.api_key = api_key

        # Инициализация клиента OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )

        self.model = "anthropic/claude-sonnet-4.5"
        self.current_df = None
        self.max_retries = 3

        # Настройки для графиков
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['figure.dpi'] = 100

    def load_csv_from_bytes(self, file_bytes: bytes, filename: str = "data.csv") -> pd.DataFrame:
        """
        Загрузить CSV из байтов

        Args:
            file_bytes: Байты CSV файла
            filename: Имя файла (для отладки)

        Returns:
            DataFrame с данными
        """
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
            self.current_df = df
            return df
        except Exception as e:
            raise Exception(f"Ошибка при загрузке CSV файла: {str(e)}")

    def load_csv_from_file(self, file_path: str) -> pd.DataFrame:
        """
        Загрузить CSV из пути

        Args:
            file_path: Путь к файлу

        Returns:
            DataFrame
        """
        try:
            df = pd.read_csv(file_path)
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
            "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
            "missing_values": {col: int(count) for col, count in df.isnull().sum().items()},
            "sample_data": df.head(5).to_dict(orient='records'),
            "summary_stats": {}
        }

        # Статистика для числовых колонок
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            stats_df = df[numeric_cols].describe()
            schema["summary_stats"] = {
                col: {stat: float(val) for stat, val in stats_df[col].items()}
                for col in numeric_cols
            }

        return schema

    def execute_python_code(self, code: str, df: pd.DataFrame) -> Tuple[bool, Any, str, List[str]]:
        """
        Безопасное выполнение Python кода с возвращением изображений в base64

        Args:
            code: Python код для выполнения
            df: DataFrame для работы

        Returns:
            Кортеж (успех, результат, вывод/ошибка, список base64 изображений)
        """
        local_vars = {
            'df': df.copy(),
            'pd': pd,
            'np': np,
            'plt': plt,
            'sns': sns,
            'result': None
        }

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        plot_base64_list = []

        try:
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):

                # Выполняем код
                exec(code, local_vars)

                # Получаем результат
                result = local_vars.get('result', None)
                output = stdout_capture.getvalue()

                # Конвертируем результат в JSON-serializable формат
                if isinstance(result, pd.DataFrame):
                    # Возвращаем DataFrame с метаданными для правильного отображения таблиц
                    result = {
                        "type": "dataframe",
                        "data": result.to_dict(orient='records'),
                        "columns": result.columns.tolist(),
                        "shape": {"rows": int(result.shape[0]), "columns": int(result.shape[1])},
                        "dtypes": {col: str(dtype) for col, dtype in result.dtypes.items()}
                    }
                elif isinstance(result, pd.Series):
                    result = result.to_dict()
                elif isinstance(result, np.ndarray):
                    result = result.tolist()
                elif isinstance(result, (np.integer, np.floating)):
                    result = float(result)
                elif isinstance(result, str) and '\n' in result:
                    # Автоматически конвертируем строки с переносами в список
                    # Это улучшит отображение на фронтенде
                    lines = [line.strip() for line in result.split('\n') if line.strip()]
                    if len(lines) > 1:  # Если это действительно список, а не просто текст
                        result = lines

                # Сохраняем графики в base64
                if plt.get_fignums():
                    for fig_num in plt.get_fignums():
                        fig = plt.figure(fig_num)

                        # Сохраняем в буфер
                        buffer = io.BytesIO()
                        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
                        buffer.seek(0)

                        # Конвертируем в base64
                        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                        plot_base64_list.append(f"data:image/png;base64,{img_base64}")

                        buffer.close()

                    plt.close('all')

                return True, result, output, plot_base64_list

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return False, None, error_msg, []
        finally:
            plt.close('all')

    def generate_code_with_retry(self, user_query: str, schema: Dict,
                                 chat_history: List[Dict] = None,
                                 previous_error: Optional[str] = None) -> str:
        """
        Генерация Python кода с помощью Claude с учетом истории

        Args:
            user_query: Запрос пользователя
            schema: Схема данных CSV
            chat_history: История предыдущих сообщений
            previous_error: Предыдущая ошибка (для повторной попытки)

        Returns:
            Сгенерированный Python код
        """
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
10. Учитывай контекст предыдущих вопросов и ответов

ВАЖНО - Форматирование результатов:
11. Для списка значений ВСЕГДА возвращай list или Series (НЕ строку с \\n)
12. Для таблиц возвращай DataFrame
13. Для одного значения возвращай число или строку
14. НИКОГДА не используй '\\n'.join() для результата - всегда возвращай list
15. Примеры правильного формата:
    - Список штатов: result = df['State'].unique().tolist()  # ✅ ПРАВИЛЬНО
    - НЕ ДЕЛАЙ ТАК: result = '\\n'.join(states)  # ❌ НЕПРАВИЛЬНО
"""

        # Формируем сообщение с данными
        user_message = f"""
Данные CSV файла:
- Колонки: {schema['columns']}
- Типы данных: {schema['dtypes']}
- Размер: {schema['shape']['rows']} строк, {schema['shape']['columns']} колонок
- Пропущенные значения: {schema['missing_values']}
- Примеры данных (первые 5 строк):
{json.dumps(schema['sample_data'], indent=2, ensure_ascii=False)}

Запрос пользователя: {user_query}
"""

        # Добавляем историю если есть
        if chat_history and len(chat_history) > 0:
            history_text = "\n\nИстория предыдущих запросов и результатов:\n"
            for i, item in enumerate(chat_history[-5:], 1):  # Последние 5 сообщений
                history_text += f"\n{i}. Запрос: {item.get('query', '')}\n"
                if item.get('success'):
                    history_text += f"   Результат: {item.get('text_output', '')[:200]}\n"
            user_message += history_text

        if previous_error:
            user_message += f"""

ПРЕДЫДУЩАЯ ПОПЫТКА ЗАВЕРШИЛАСЬ ОШИБКОЙ:
{previous_error}

Исправь код, учитывая эту ошибку. Напиши исправленную версию кода.
"""

        # Формируем сообщения для API
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

    def analyze(self, user_query: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Основной метод анализа для API

        Args:
            user_query: Запрос пользователя
            chat_history: История предыдущих сообщений

        Returns:
            Словарь с результатами в формате API
        """
        if self.current_df is None:
            return {
                "success": False,
                "error": "CSV файл не загружен",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Получаем схему данных
        schema = self.analyze_csv_schema(self.current_df)

        result = {
            "success": False,
            "query": user_query,
            "code_attempts": [],
            "final_code": None,
            "result_data": None,
            "text_output": None,
            "plots": [],
            "error": None,
            "attempts_count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Пробуем выполнить с повторными попытками
        previous_error = None

        for attempt in range(self.max_retries):
            result["attempts_count"] = attempt + 1

            # Генерируем код
            try:
                code = self.generate_code_with_retry(
                    user_query,
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

            # Выполняем код
            success, exec_result, output, plot_base64_list = self.execute_python_code(
                code, self.current_df
            )

            if success:
                result["success"] = True
                result["final_code"] = code
                result["result_data"] = exec_result
                result["text_output"] = output
                result["plots"] = plot_base64_list
                result["code_attempts"][-1]["success"] = True
                break
            else:
                previous_error = output
                result["code_attempts"][-1]["error"] = output

                if attempt == self.max_retries - 1:
                    result["error"] = f"Не удалось выполнить код после {self.max_retries} попыток"
                    result["error_details"] = output

        return result

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Получить информацию о текущем CSV файле

        Returns:
            Информация о схеме данных
        """
        if self.current_df is None:
            return {
                "success": False,
                "error": "CSV файл не загружен"
            }

        schema = self.analyze_csv_schema(self.current_df)
        return {
            "success": True,
            "schema": schema,
            "timestamp": datetime.utcnow().isoformat()
        }
