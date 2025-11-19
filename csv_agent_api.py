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
        self.dataframes = {}  # Хранилище для множественных DataFrame: {filename: df}
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
            filename: Имя файла

        Returns:
            DataFrame с данными
        """
        try:
            # Автоопределение разделителя (поддержка , и ; и других)
            df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')
            self.current_df = df
            # Сохраняем в хранилище множественных файлов
            clean_name = Path(filename).stem  # Убираем расширение
            self.dataframes[clean_name] = df
            return df
        except Exception as e:
            raise Exception(f"Ошибка при загрузке CSV файла '{filename}': {str(e)}")

    def load_multiple_csv(self, files_data: List[Tuple[bytes, str]]) -> Dict[str, pd.DataFrame]:
        """
        Загрузить несколько CSV файлов одновременно

        Args:
            files_data: Список кортежей (file_bytes, filename)

        Returns:
            Словарь {filename: DataFrame}
        """
        loaded = {}
        for file_bytes, filename in files_data:
            df = self.load_csv_from_bytes(file_bytes, filename)
            clean_name = Path(filename).stem
            loaded[clean_name] = df

        # Первый файл - основной
        if files_data:
            self.current_df = loaded[Path(files_data[0][1]).stem]

        return loaded

    def load_csv_from_file(self, file_path: str) -> pd.DataFrame:
        """
        Загрузить CSV из пути

        Args:
            file_path: Путь к файлу

        Returns:
            DataFrame
        """
        try:
            # Автоопределение разделителя (поддержка , и ; и других)
            df = pd.read_csv(file_path, sep=None, engine='python')
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
            df: DataFrame для работы (основной)

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

        # Добавляем все загруженные DataFrame'ы
        for name, dataframe in self.dataframes.items():
            local_vars[name] = dataframe.copy()

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
                # Теперь result - это Markdown строка, оставляем как есть
                # Нужно только обработать специальные типы Python
                if isinstance(result, (np.integer, np.floating)):
                    result = float(result)
                elif isinstance(result, np.ndarray):
                    result = result.tolist()
                elif isinstance(result, pd.DataFrame) or isinstance(result, pd.Series):
                    # Если AI вернул DataFrame вместо Markdown - конвертируем в строку
                    result = str(result)
                # Все остальное (строки, числа, списки) оставляем как есть

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
2. Доступные DataFrame'ы: 'df' (основной){available_dataframes}
3. Для визуализации используй matplotlib/seaborn
4. Код должен быть безопасным и эффективным
5. Всегда проверяй существование колонок перед использованием
6. Обрабатывай возможные ошибки (NaN, типы данных и т.д.)
7. Возвращай ТОЛЬКО код Python, без объяснений и markdown разметки

КРИТИЧЕСКИ ВАЖНО - Очистка данных:
7a. **ВСЕГДА** начинай с очистки данных:
   ```python
   # Удаляем полностью пустые строки
   df = df.dropna(how='all')

   # Если первая строка содержит заголовки (а текущие заголовки - Unnamed), обнови их
   if 'Unnamed' in str(df.columns):
       # Ищем строку с настоящими заголовками
       for i in range(min(5, len(df))):
           if df.iloc[i].notna().sum() > len(df.columns) * 0.5:  # Больше 50% непустых
               df.columns = df.iloc[i].values
               df = df.iloc[i+1:].reset_index(drop=True)
               break

   # Удаляем строки где все значения NaN
   df = df.dropna(how='all')
   ```
7b. **ВСЕГДА** показывай диагностическую информацию:
   ```python
   print(f"Очищенные данные: {len(df)} строк")
   print(f"Колонки: {list(df.columns)}")
   print(f"Первые 3 строки:\\n{df.head(3)}")
   ```
7c. При поиске колонок используй case-insensitive поиск и частичное совпадение:
   ```python
   # Пример: найти колонку с "revenue" или "выручка"
   revenue_col = None
   for col in df.columns:
       if 'revenue' in str(col).lower() or 'выручка' in str(col).lower():
           revenue_col = col
           break
   ```

ВАЖНО - Форматирование результата:
8. **ОБЯЗАТЕЛЬНО** возвращай результат в переменной 'result' как **Markdown строку**
9. Используй Markdown для красивого форматирования:
   - Заголовки: ## Заголовок, ### Подзаголовок
   - Таблицы: | Колонка | Значение | (с разделителями |---|---|)
   - Списки: - элемент или 1. элемент
   - Выделение: **жирный**, *курсив*
   - Разделители: --- для горизонтальной линии
10. Структура Markdown ответа:
    - Начни с краткого объяснения (1-2 предложения)
    - Используй заголовки для разделов
    - Выводи данные в таблицах или списках
    - Добавь выводы и анализ в конце
11. Графики выводи через plt.show() как обычно (отдельно от result)
12. **НЕ ДУБЛИРУЙ результат!** Используй print() ТОЛЬКО для процесса работы, НЕ для финального результата:
    - ✅ ПРАВИЛЬНО: print("Анализирую данные...") в начале
    - ❌ НЕПРАВИЛЬНО: print(result) в конце
    - Финальный результат должен быть ТОЛЬКО в переменной result

Пример хорошего результата:
```python
# Логи процесса (будут показаны отдельно в text_output)
print("Анализирую данные о продажах...")
print(f"Загружено {len(df)} записей")

# Анализируем данные
total = df['Revenue'].sum()
avg = df['Revenue'].mean()

print("Расчеты завершены, формирую отчет...")

# Формируем ТОЛЬКО результат в Markdown (НЕ выводим через print!)
result = f\"\"\"
## Анализ продаж

Проанализировал данные по {len(df)} записям.

### Основные метрики

| Метрика | Значение |
|---------|----------|
| Общая выручка | ${total:,.2f} |
| Средняя выручка | ${avg:,.2f} |

### Топ-5 стран по выручке

{df.groupby('Country')['Revenue'].sum().nlargest(5).to_markdown()}

---

**Вывод:** Бизнес показывает стабильный рост с рентабельностью 29.5%
\"\"\"

# ❌ НЕ ДЕЛАЙ ТАК: print(result)  # Создаст дубликат на фронтенде!
```
"""

        # Добавляем информацию о дополнительных файлах в промпт
        available_dataframes_text = ""
        if len(self.dataframes) > 1:
            other_files = [name for name in self.dataframes.keys() if self.dataframes[name] is not self.current_df]
            if other_files:
                # Формируем список имен файлов с кавычками
                names_quoted = [f"'{name}'" for name in other_files]
                available_dataframes_text = f", {', '.join(names_quoted)}"

        system_prompt = system_prompt.replace("{available_dataframes}", available_dataframes_text)

        # Формируем сообщение с данными
        files_info = ""
        if len(self.dataframes) > 1:
            files_info = "\n\nДоступные дополнительные файлы:\n"
            for name, df_other in self.dataframes.items():
                if df_other is not self.current_df:
                    files_info += f"- '{name}': {df_other.shape[0]} строк, {df_other.shape[1]} колонок, колонки: {list(df_other.columns)}\n"

        user_message = f"""
Данные CSV файла (основной):
- Колонки: {schema['columns']}
- Типы данных: {schema['dtypes']}
- Размер: {schema['shape']['rows']} строк, {schema['shape']['columns']} колонок
- Пропущенные значения: {schema['missing_values']}
- Примеры данных (первые 5 строк):
{json.dumps(schema['sample_data'], indent=2, ensure_ascii=False)}{files_info}

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
