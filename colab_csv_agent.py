"""
AI-агент для анализа CSV файлов - версия для Google Colab
Использует Claude Sonnet 4.5 через OpenRouter
"""

import os
import sys
import io
import json
import traceback
from typing import Dict, List, Optional, Tuple, Any
import contextlib

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI
from IPython.display import display, Image, Markdown


class ColabCSVAgent:
    """
    AI-агент для анализа CSV файлов в Google Colab
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
        self.current_csv_name = None
        self.current_df = None
        self.conversation_history = []
        self.max_retries = 3

        # Настройки для графиков
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 6)
        plt.rcParams['figure.dpi'] = 100

        print("✓ AI CSV Agent инициализирован")
        print(f"✓ Модель: {self.model}")

    def load_csv_from_upload(self, uploaded_files: dict) -> pd.DataFrame:
        """
        Загрузка CSV из загруженных файлов Colab

        Args:
            uploaded_files: Словарь файлов из files.upload()

        Returns:
            DataFrame
        """
        if not uploaded_files:
            raise Exception("Файлы не загружены")

        # Берем первый CSV файл
        csv_file = None
        for filename, content in uploaded_files.items():
            if filename.endswith('.csv'):
                csv_file = filename
                break

        if not csv_file:
            raise Exception("CSV файл не найден среди загруженных")

        # Загружаем DataFrame
        df = pd.read_csv(io.BytesIO(uploaded_files[csv_file]))
        self.current_csv_name = csv_file
        self.current_df = df

        print(f"✓ Загружен файл: {csv_file}")
        print(f"✓ Размер: {df.shape[0]} строк, {df.shape[1]} колонок")
        print(f"✓ Колонки: {', '.join(df.columns)}")

        return df

    def load_csv_from_path(self, file_path: str) -> pd.DataFrame:
        """
        Загрузка CSV из пути

        Args:
            file_path: Путь к CSV файлу

        Returns:
            DataFrame
        """
        df = pd.read_csv(file_path)
        self.current_csv_name = file_path
        self.current_df = df

        print(f"✓ Загружен файл: {file_path}")
        print(f"✓ Размер: {df.shape[0]} строк, {df.shape[1]} колонок")
        print(f"✓ Колонки: {', '.join(df.columns)}")

        return df

    def analyze_csv_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Анализ схемы CSV"""
        schema = {
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "shape": df.shape,
            "missing_values": df.isnull().sum().to_dict(),
            "sample_data": df.head(5).to_dict(orient='records'),
            "summary_stats": {}
        }

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            schema["summary_stats"] = df[numeric_cols].describe().to_dict()

        return schema

    def execute_python_code(self, code: str, df: pd.DataFrame) -> Tuple[bool, Any, str, List[str]]:
        """
        Выполнение Python кода с сохранением графиков

        Returns:
            (успех, результат, вывод, список путей к графикам)
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
        plot_paths = []

        try:
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):

                exec(code, local_vars)
                result = local_vars.get('result', None)
                output = stdout_capture.getvalue()

                # Сохраняем графики
                if plt.get_fignums():
                    for i, fig_num in enumerate(plt.get_fignums()):
                        fig = plt.figure(fig_num)
                        fig_path = f"plot_{len(self.conversation_history)}_{fig_num}.png"
                        fig.savefig(fig_path, bbox_inches='tight', dpi=150)
                        plot_paths.append(fig_path)

                    plt.close('all')

                return True, result, output, plot_paths

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return False, None, error_msg, []
        finally:
            plt.close('all')

    def generate_code_with_retry(self, user_query: str, schema: Dict,
                                 previous_error: Optional[str] = None) -> str:
        """Генерация кода с помощью Claude"""

        system_prompt = """Ты - эксперт по анализу данных на Python.
Твоя задача - писать качественный Python код для анализа CSV данных в Google Colab.

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
10. Для графиков используй plt.figure() для создания новых фигур
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

Исправь код, учитывая эту ошибку.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=4000
            )

            code = response.choices[0].message.content.strip()

            # Убираем markdown
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]

            return code.strip()

        except Exception as e:
            raise Exception(f"Ошибка при генерации кода: {str(e)}")

    def analyze(self, user_query: str, show_code: bool = True) -> Dict[str, Any]:
        """
        Основной метод анализа для Colab

        Args:
            user_query: Запрос пользователя
            show_code: Показывать ли сгенерированный код

        Returns:
            Словарь с результатами
        """
        if self.current_df is None:
            print("❌ Ошибка: CSV файл не загружен")
            return {"success": False, "error": "CSV файл не загружен"}

        schema = self.analyze_csv_schema(self.current_df)

        result = {
            "success": False,
            "query": user_query,
            "code_attempts": [],
            "final_result": None,
            "output": None,
            "plots": [],
            "error": None
        }

        previous_error = None

        for attempt in range(self.max_retries):
            display(Markdown(f"### 🔄 Попытка {attempt + 1}/{self.max_retries}"))

            # Генерация кода
            try:
                code = self.generate_code_with_retry(user_query, schema, previous_error)

                if show_code:
                    display(Markdown("**Сгенерированный код:**"))
                    display(Markdown(f"```python\n{code}\n```"))

                result["code_attempts"].append({
                    "attempt": attempt + 1,
                    "code": code
                })

            except Exception as e:
                result["error"] = f"Ошибка генерации кода: {str(e)}"
                display(Markdown(f"❌ **Ошибка:** {result['error']}"))
                break

            # Выполнение кода
            success, exec_result, output, plot_paths = self.execute_python_code(
                code, self.current_df
            )

            if success:
                display(Markdown("### ✅ Код выполнен успешно!"))

                if output:
                    display(Markdown("**Вывод:**"))
                    print(output)

                if exec_result is not None:
                    display(Markdown("**Результат:**"))
                    if isinstance(exec_result, pd.DataFrame):
                        display(exec_result)
                    else:
                        print(exec_result)

                # Показываем графики
                if plot_paths:
                    display(Markdown("**Графики:**"))
                    for plot_path in plot_paths:
                        display(Image(plot_path))

                result["success"] = True
                result["final_result"] = exec_result
                result["output"] = output
                result["plots"] = plot_paths
                result["code_attempts"][-1]["success"] = True
                break

            else:
                display(Markdown(f"### ❌ Ошибка выполнения:"))
                display(Markdown(f"```\n{output}\n```"))

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

    def show_schema(self):
        """Показать структуру данных"""
        if self.current_df is None:
            print("❌ CSV файл не загружен")
            return

        schema = self.analyze_csv_schema(self.current_df)

        display(Markdown("## 📊 Структура данных"))
        display(Markdown(f"**Файл:** {self.current_csv_name}"))
        display(Markdown(f"**Размер:** {schema['shape'][0]} строк × {schema['shape'][1]} колонок"))

        display(Markdown("### Колонки и типы данных:"))
        dtype_df = pd.DataFrame([
            {"Колонка": col, "Тип": dtype}
            for col, dtype in schema['dtypes'].items()
        ])
        display(dtype_df)

        display(Markdown("### Пропущенные значения:"))
        missing_df = pd.DataFrame([
            {"Колонка": col, "Пропущено": count}
            for col, count in schema['missing_values'].items()
            if count > 0
        ])
        if len(missing_df) > 0:
            display(missing_df)
        else:
            display(Markdown("*Пропущенных значений нет*"))

        display(Markdown("### Первые 5 строк:"))
        display(self.current_df.head())


# Вспомогательные функции для удобства использования в Colab

def setup_agent(api_key: str = None) -> ColabCSVAgent:
    """
    Быстрая настройка агента

    Args:
        api_key: API ключ OpenRouter (если None, попытается взять из переменной окружения)

    Returns:
        Настроенный агент
    """
    if api_key is None:
        api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        display(Markdown("""
        ## ⚠️ API ключ не найден

        Получите ключ на https://openrouter.ai/keys и установите его:

        ```python
        import os
        os.environ['OPENROUTER_API_KEY'] = 'ваш_ключ_здесь'
        agent = setup_agent()
        ```

        Или передайте напрямую:

        ```python
        agent = setup_agent(api_key='ваш_ключ_здесь')
        ```
        """))
        return None

    return ColabCSVAgent(api_key)


def upload_and_analyze(agent: ColabCSVAgent = None, api_key: str = None):
    """
    Загрузка CSV и создание агента в одну команду

    Args:
        agent: Существующий агент (опционально)
        api_key: API ключ (если агент не передан)

    Returns:
        Агент с загруженным CSV
    """
    from google.colab import files

    # Создаем агента если нужно
    if agent is None:
        agent = setup_agent(api_key)
        if agent is None:
            return None

    # Загружаем файл
    display(Markdown("## 📁 Загрузите CSV файл"))
    uploaded = files.upload()

    if uploaded:
        agent.load_csv_from_upload(uploaded)
        agent.show_schema()
        display(Markdown("""
        ---
        ## 💬 Готово к анализу!

        Теперь вы можете задавать вопросы:

        ```python
        agent.analyze("Покажи статистику по всем колонкам")
        agent.analyze("Построй график распределения")
        agent.analyze("Найди корреляции между колонками")
        ```
        """))

    return agent


# Пример использования
if __name__ == "__main__":
    display(Markdown("""
    # 🤖 AI CSV Analysis Agent для Google Colab

    Powered by Claude Sonnet 4.5 via OpenRouter

    ## Быстрый старт:

    ```python
    # 1. Загрузите CSV и создайте агента
    agent = upload_and_analyze(api_key='your_api_key')

    # 2. Задавайте вопросы о данных
    agent.analyze("Какая средняя цена?")
    agent.analyze("Построй гистограмму распределения возраста")
    agent.analyze("Покажи топ-10 записей по продажам")

    # 3. Просмотр структуры данных
    agent.show_schema()
    ```
    """))
