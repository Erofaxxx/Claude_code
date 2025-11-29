"""
API-версия CSV Analysis Agent для интеграции с внешними сервисами
Julius.ai style - многоэтапный анализ с красивым выводом результатов
Поддерживает историю диалога и возвращает результаты в JSON с base64 изображениями
"""

import os
import io
import json
import traceback
import gc
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


# Конфигурация доступных моделей
AVAILABLE_MODELS = {
    "claude-sonnet-4.5": {
        "id": "anthropic/claude-sonnet-4.5",
        "name": "Claude Sonnet 4.5",
        "provider": "Anthropic",
        "description": "Лучшая модель для сложного анализа данных и генерации кода",
        "context_length": 200000,
        "recommended": True
    },
    "gpt-4o": {
        "id": "openai/gpt-4o",
        "name": "GPT-4o",
        "provider": "OpenAI",
        "description": "Мощная модель от OpenAI с отличным пониманием данных",
        "context_length": 128000,
        "recommended": True
    },
    "deepseek-chat": {
        "id": "deepseek/deepseek-chat",
        "name": "DeepSeek Chat",
        "provider": "DeepSeek",
        "description": "Быстрая и эффективная модель для анализа данных",
        "context_length": 64000,
        "recommended": False
    },
    "qwen-2.5-72b": {
        "id": "qwen/qwen-2.5-72b-instruct",
        "name": "Qwen 2.5 72B",
        "provider": "Alibaba",
        "description": "Открытая модель с отличным качеством",
        "context_length": 32000,
        "recommended": False
    },
    "llama-3.3-70b": {
        "id": "meta-llama/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B",
        "provider": "Meta",
        "description": "Открытая модель от Meta с хорошими аналитическими способностями",
        "context_length": 128000,
        "recommended": False
    }
}

# Модель по умолчанию
DEFAULT_MODEL = "claude-sonnet-4.5"


class CSVAnalysisAgentAPI:
    """
    API-версия агента для анализа CSV файлов (Julius.ai style)
    Поддерживает историю диалога и возвращает результаты в формате API
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        """
        Инициализация агента

        Args:
            api_key: API ключ для OpenRouter
            model: Короткое имя модели (например, "claude-sonnet-4.5", "gpt-4o")
                   По умолчанию используется Claude Sonnet 4.5
        """
        self.api_key = api_key

        # Инициализация клиента OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )

        # Проверка и установка модели
        if model not in AVAILABLE_MODELS:
            raise ValueError(
                f"Модель '{model}' не поддерживается. "
                f"Доступные модели: {', '.join(AVAILABLE_MODELS.keys())}"
            )

        self.model_key = model  # Короткое имя (ключ)
        self.model = AVAILABLE_MODELS[model]["id"]  # Полный ID для API
        self.model_info = AVAILABLE_MODELS[model]  # Полная информация о модели

        self.current_df = None
        self.original_df = None  # Храним оригинал
        self.dataframes = {}  # Хранилище для множественных DataFrame: {filename: df}
        self.max_retries = 3

        # Метаданные о данных
        self.data_metadata = {
            "has_unnamed_columns": False,
            "first_row_is_header": False,
            "columns_cleaned": False,
            "rows_removed": 0,
            "cols_removed": 0
        }

        # Настройки для графиков
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['figure.dpi'] = 100

    def _is_first_row_header(self, df: pd.DataFrame) -> bool:
        """
        Определяем является ли первая строка заголовком

        Критерии:
        1. Текущие колонки типа "Unnamed: 0", "Unnamed: 1"...
        2. Первая строка содержит текстовые значения (потенциальные названия)
        3. Вторая строка содержит числовые/смешанные значения (данные)
        """
        # Проверка 1: Много Unnamed колонок?
        unnamed_count = sum(1 for col in df.columns if 'Unnamed' in str(col))
        if unnamed_count < len(df.columns) * 0.3:  # Меньше 30% unnamed
            return False

        # Проверка 2: Первая строка - текст?
        if len(df) < 2:
            return False

        first_row = df.iloc[0]
        second_row = df.iloc[1]

        # Считаем текстовые значения в первой строке
        text_count_row1 = sum(1 for val in first_row if isinstance(val, str) and not str(val).replace('.', '').replace('-', '').isdigit())

        # Считаем числовые значения во второй строке
        numeric_count_row2 = sum(1 for val in second_row if pd.notna(val) and (isinstance(val, (int, float)) or str(val).replace('.', '').replace('-', '').isdigit()))

        # Если первая строка преимущественно текст, а вторая - числа
        return text_count_row1 > len(first_row) * 0.5 and numeric_count_row2 > len(second_row) * 0.3

    def smart_load_csv(self, file_bytes: bytes, filename: str = "data.csv") -> Dict[str, Any]:
        """
        Умная загрузка CSV с автоматическим анализом структуры
        Работает как Julius.ai - сначала понимает структуру, потом очищает

        Returns:
            Dict с информацией о загрузке и очистке
        """
        load_info = {
            "filename": filename,
            "steps": [],
            "warnings": [],
            "original_shape": None,
            "final_shape": None,
            "success": True
        }

        try:
            # ШАГ 1: Загружаем "как есть"
            df_raw = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')
            self.original_df = df_raw.copy()
            load_info["original_shape"] = df_raw.shape
            load_info["steps"].append(f"📥 Загружено: {df_raw.shape[0]} строк × {df_raw.shape[1]} колонок")

            # ШАГ 2: Проверяем "Unnamed" колонки
            unnamed_cols = [col for col in df_raw.columns if 'Unnamed' in str(col)]
            if unnamed_cols:
                self.data_metadata["has_unnamed_columns"] = True
                load_info["warnings"].append(
                    f"⚠️ Найдено {len(unnamed_cols)} колонок типа 'Unnamed'. "
                    f"Возможно первая строка - это заголовки."
                )
                load_info["steps"].append(f"🔍 Обнаружено {len(unnamed_cols)} безымянных колонок")

            # ШАГ 3: Проверяем первую строку - может это заголовки?
            if self._is_first_row_header(df_raw):
                self.data_metadata["first_row_is_header"] = True
                load_info["steps"].append("🎯 Обнаружено: первая строка - это заголовки данных")

                # Делаем первую строку заголовком
                new_columns = df_raw.iloc[0].tolist()
                df_raw.columns = new_columns
                df_raw = df_raw.iloc[1:].reset_index(drop=True)

                load_info["steps"].append("✅ Первая строка преобразована в заголовки")

            # ШАГ 4: Очищаем названия колонок от пробелов
            original_cols = list(df_raw.columns)
            df_raw.columns = df_raw.columns.astype(str).str.strip()
            cleaned_cols = list(df_raw.columns)

            if original_cols != cleaned_cols:
                self.data_metadata["columns_cleaned"] = True
                load_info["steps"].append("🧹 Очищены названия колонок от лишних пробелов")

            # ШАГ 5: Удаляем полностью пустые строки
            rows_before = len(df_raw)
            df_raw = df_raw.dropna(how='all')
            rows_after = len(df_raw)
            rows_removed = rows_before - rows_after

            if rows_removed > 0:
                self.data_metadata["rows_removed"] = rows_removed
                load_info["steps"].append(f"🗑️ Удалено {rows_removed} пустых строк")

            # ШАГ 6: Удаляем полностью пустые колонки
            cols_before = len(df_raw.columns)
            df_raw = df_raw.dropna(axis=1, how='all')
            cols_after = len(df_raw.columns)
            cols_removed = cols_before - cols_after

            if cols_removed > 0:
                self.data_metadata["cols_removed"] = cols_removed
                load_info["steps"].append(f"🗑️ Удалено {cols_removed} пустых колонок")

            # Сохраняем результат
            self.current_df = df_raw.reset_index(drop=True)
            clean_name = Path(filename).stem
            self.dataframes[clean_name] = self.current_df

            load_info["final_shape"] = self.current_df.shape
            load_info["steps"].append(
                f"✅ Итого: {self.current_df.shape[0]} строк × {self.current_df.shape[1]} колонок"
            )

            return load_info

        except Exception as e:
            load_info["success"] = False
            load_info["error"] = str(e)
            raise Exception(f"Ошибка при загрузке CSV файла '{filename}': {str(e)}")

    def load_csv_from_bytes(self, file_bytes: bytes, filename: str = "data.csv") -> pd.DataFrame:
        """
        Загрузить CSV из байтов (с умной очисткой)

        Args:
            file_bytes: Байты CSV файла
            filename: Имя файла

        Returns:
            DataFrame с данными
        """
        self.smart_load_csv(file_bytes, filename)
        return self.current_df

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
            self.smart_load_csv(file_bytes, filename)
            clean_name = Path(filename).stem
            loaded[clean_name] = self.dataframes[clean_name]

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
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        return self.load_csv_from_bytes(file_bytes, os.path.basename(file_path))

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
            "summary_stats": {},
            "metadata": self.data_metadata
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
                if isinstance(result, (np.integer, np.floating)):
                    result = float(result)
                elif isinstance(result, np.ndarray):
                    result = result.tolist()
                elif isinstance(result, pd.DataFrame) or isinstance(result, pd.Series):
                    # Если AI вернул DataFrame вместо Markdown - конвертируем в строку
                    result = str(result)

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
            # Полная очистка matplotlib
            plt.close('all')
            plt.clf()
            # Очищаем локальные переменные
            local_vars.clear()

    def generate_code_with_retry(self, user_query: str, schema: Dict,
                                 chat_history: List[Dict] = None,
                                 previous_error: Optional[str] = None) -> str:
        """
        Генерация Python кода с помощью AI (Julius.ai style - многоэтапный подход)

        Args:
            user_query: Запрос пользователя
            schema: Схема данных CSV
            chat_history: История предыдущих сообщений
            previous_error: Предыдущая ошибка (для повторной попытки)

        Returns:
            Сгенерированный Python код
        """
        system_prompt = """Ты эксперт-аналитик данных, работающий как Julius.ai.

🎯 ТВОЯ ЗАДАЧА: Писать код который работает ПОЭТАПНО и ЛОГИРУЕТ каждый шаг.

📋 ОБЯЗАТЕЛЬНАЯ СТРУКТУРА КОДА:

```python
# === ШАГ 1: ПОНИМАНИЕ ДАННЫХ ===
print("🔍 ШАГ 1: Изучаю структуру данных...")
print(f"Размер данных: {len(df)} строк, {len(df.columns)} колонок")
print(f"Колонки: {list(df.columns)}")

# === ШАГ 2: ПРОВЕРКА И ОЧИСТКА ===
print("\\n🧹 ШАГ 2: Проверяю качество данных...")

# Ищем нужные колонки (гибкий поиск)
def find_column(df, keywords):
    for col in df.columns:
        col_lower = str(col).lower()
        if any(keyword.lower() in col_lower for keyword in keywords):
            return col
    return None

year_col = find_column(df, ['year', 'год', 'date'])
amount_col = find_column(df, ['amount', 'сумма', 'total', 'value'])

if not year_col or not amount_col:
    result = f"❌ Ошибка: не найдены нужные колонки. Доступные: {list(df.columns)}"
else:
    print(f"✅ Найдены колонки: {year_col}, {amount_col}")

    # Преобразуем типы данных
    df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
    df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')

    # Удаляем строки с пустыми значениями
    df_clean = df.dropna(subset=[year_col, amount_col])
    print(f"✅ Данные очищены: {len(df_clean)} валидных строк")

    # === ШАГ 3: АНАЛИЗ ===
    print("\\n📊 ШАГ 3: Выполняю анализ...")

    # Группировка и агрегация
    result_df = df_clean.groupby(year_col)[amount_col].sum().reset_index()
    result_df = result_df.sort_values(year_col)

    print(f"✅ Агрегировано: {len(result_df)} групп")

    # === ШАГ 4: ВИЗУАЛИЗАЦИЯ ===
    print("\\n📈 ШАГ 4: Создаю визуализацию...")

    plt.figure(figsize=(12, 6))
    plt.plot(result_df[year_col], result_df[amount_col],
             marker='o', linewidth=2, markersize=8)
    plt.title('Динамика показателей', fontsize=16, fontweight='bold')
    plt.xlabel(year_col, fontsize=12)
    plt.ylabel(amount_col, fontsize=12)
    plt.grid(True, alpha=0.3)

    # Форматируем ось Y с запятыми
    ax = plt.gca()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

    plt.tight_layout()
    print("✅ График создан")

    # === ШАГ 5: ФОРМАТИРОВАННЫЙ РЕЗУЛЬТАТ ===
    print("\\n✅ ШАГ 5: Формирую финальный отчет...")

    # Создаем MARKDOWN таблицу (НЕ код-блок!)
    display_df = result_df.copy()

    # Форматируем числа
    display_df[amount_col] = display_df[amount_col].apply(lambda x: f"{x:,.0f}")

    # Генерируем Markdown таблицу ВРУЧНУЮ
    markdown_table = f"| {year_col} | {amount_col} |\\n"
    markdown_table += "|" + "-" * (len(str(year_col)) + 2) + "|" + "-" * (len(str(amount_col)) + 2) + "|\\n"

    for _, row in display_df.iterrows():
        markdown_table += f"| {int(row[year_col])} | {row[amount_col]} |\\n"

    # Статистика
    total_sum = result_df[amount_col].sum()
    avg_value = result_df[amount_col].mean()

    result = f\"\"\"
## 📊 Результаты анализа

### 📈 Данные по годам

{markdown_table}

### 📌 Статистика

| Показатель | Значение |
|------------|----------|
| Всего записей | {len(df_clean)} |
| Общая сумма | {total_sum:,.0f} |
| Среднее значение | {avg_value:,.0f} |

✅ Анализ выполнен успешно
\"\"\"

    print("✅ Анализ завершен успешно!")
```

🎯 КЛЮЧЕВЫЕ ПРАВИЛА:

1. **ЛОГИРУЙ КАЖДЫЙ ШАГ** через print():
   - Что делаешь сейчас
   - Сколько данных обработано
   - Какие промежуточные результаты

2. **ИЩИ КОЛОНКИ ГИБКО**:
   - Используй функцию find_column()
   - Ищи по ключевым словам
   - Проверяй существование

3. **ПРОВЕРЯЙ ВСЁ**:
   - Существование колонок
   - Типы данных
   - Пустые значения

4. **ФОРМАТИРУЙ ЧИСЛА**:
   - В таблицах: `{value:,.0f}` или `{value:,.2f}`
   - На графиках: `plt.FuncFormatter(lambda x, p: f'{x:,.0f}')`

5. **СОЗДАВАЙ MARKDOWN ТАБЛИЦЫ** (НЕ код-блоки!):
   - Используй формат: `| Колонка | Значение |`
   - Разделитель: `|---------|----------|`
   - Генерируй таблицу циклом или через петлю
   - НЕ используй ``` вокруг таблиц!
   - Форматируй числа ПЕРЕД выводом

6. **result В MARKDOWN**:
   - Заголовки ##, ###
   - Таблицы НАПРЯМУЮ в Markdown (| col | val |)
   - Эмодзи для наглядности
   - **НЕ ПЕЧАТАЙ result через print!**
   - **НЕ ИСПОЛЬЗУЙ ``` вокруг таблиц данных!**

7. **ОБРАБОТКА ОШИБОК**:
   - Если колонки не найдены - сообщи об этом в result
   - Покажи какие колонки доступны
   - Дай рекомендацию пользователю

Доступные DataFrame'ы: 'df' (основной){available_dataframes}

Помни: ты должен работать КАК НАСТОЯЩИЙ АНАЛИТИК - пошагово, с объяснениями, с проверками!
"""

        # Добавляем информацию о дополнительных файлах в промпт
        available_dataframes_text = ""
        if len(self.dataframes) > 1:
            other_files = [name for name in self.dataframes.keys()]
            if other_files:
                names_quoted = [f"'{name}'" for name in other_files]
                available_dataframes_text = f", {', '.join(names_quoted)}"

        system_prompt = system_prompt.replace("{available_dataframes}", available_dataframes_text)

        # Формируем детальное описание данных
        column_details = []
        for col in schema['columns']:
            dtype = schema['dtypes'][col]
            missing = schema['missing_values'].get(col, 0)

            # Примеры значений
            examples = []
            if len(schema['sample_data']) > 0:
                for row in schema['sample_data'][:3]:
                    val = row.get(col)
                    if pd.notna(val):
                        examples.append(str(val))

            examples_str = ", ".join(examples[:3]) if examples else "нет данных"

            col_info = f"  • '{col}' ({dtype})"
            if missing > 0:
                col_info += f" [⚠️ пустых: {missing}]"
            col_info += f"\n    Примеры: {examples_str}"
            column_details.append(col_info)

        user_message = f"""
📊 ДАННЫЕ CSV ФАЙЛА:

РАЗМЕР: {schema['shape']['rows']} строк × {schema['shape']['columns']} колонок

КОЛОНКИ:
{chr(10).join(column_details)}

ПРИМЕРЫ ПЕРВЫХ СТРОК:
{json.dumps(schema['sample_data'][:3], indent=2, ensure_ascii=False)}

🎯 ЗАПРОС ПОЛЬЗОВАТЕЛЯ: {user_query}

⚡ ВАЖНО:
- Логируй каждый шаг через print()
- Ищи колонки гибко (по ключевым словам)
- Проверяй существование колонок
- Форматируй ВСЕ числа
- Создавай красивые таблицы
"""

        if self.data_metadata.get("first_row_is_header"):
            user_message += "\n\n✅ ПРИМЕЧАНИЕ: Первая строка CSV была автоматически преобразована в заголовки."

        # Добавляем историю если есть
        if chat_history and len(chat_history) > 0:
            history_text = "\n\nИстория предыдущих запросов:\n"
            for i, item in enumerate(chat_history[-5:], 1):
                history_text += f"\n{i}. Запрос: {item.get('query', '')}\n"
                if item.get('success'):
                    history_text += f"   Результат: {item.get('text_output', '')[:200]}\n"
            user_message += history_text

        if previous_error:
            user_message += f"""

ПРЕДЫДУЩАЯ ПОПЫТКА ЗАВЕРШИЛАСЬ ОШИБКОЙ:
{previous_error}

Исправь код, учитывая эту ошибку.
"""

        # Формируем сообщения для API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Отправляем запрос к Claude/GPT
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
            error_msg = str(e)

            # Улучшенная диагностика ошибок аутентификации
            if "401" in error_msg or "Unauthorized" in error_msg or "User not found" in error_msg:
                raise Exception(
                    f"Ошибка аутентификации OpenRouter (401): API ключ неверный или истек. "
                    f"Проверьте OPENROUTER_API_KEY в .env файле. "
                    f"Получите новый ключ на https://openrouter.ai/keys. "
                    f"Детали: {error_msg}"
                )
            elif "403" in error_msg:
                raise Exception(
                    f"Доступ запрещен (403): У API ключа нет доступа к модели {self.model} "
                    f"или недостаточно кредитов. Детали: {error_msg}"
                )
            elif "429" in error_msg:
                raise Exception(
                    f"Превышен лимит запросов (429): Слишком много запросов к API. "
                    f"Подождите немного и попробуйте снова. Детали: {error_msg}"
                )
            else:
                raise Exception(f"Ошибка при генерации кода: {error_msg}")

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
            "timestamp": datetime.utcnow().isoformat(),
            "load_info": self.data_metadata
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

    def cleanup(self):
        """
        Очистка памяти после использования агента
        Вызывайте этот метод после завершения работы с агентом
        """
        # Удаляем все DataFrame'ы
        if self.current_df is not None:
            del self.current_df
            self.current_df = None

        if self.original_df is not None:
            del self.original_df
            self.original_df = None

        if self.dataframes:
            self.dataframes.clear()

        # Закрываем все matplotlib фигуры
        plt.close('all')

        # Форсируем сборку мусора
        gc.collect()
