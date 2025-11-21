"""
FastAPI сервер для CSV Analysis Agent
Интеграция с Lovable и другими frontend приложениями
"""

import os
import io
import traceback
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

from csv_agent_api import CSVAnalysisAgentAPI

# Загрузка переменных окружения
load_dotenv()

# Инициализация FastAPI
app = FastAPI(
    title="CSV Analysis Agent API",
    description="AI-powered CSV analysis with Claude Sonnet 4.5",
    version="1.0.0"
)

# CORS для работы с Lovable и другими frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API ключ для OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY не найден в переменных окружения")

# Валидация формата API ключа
OPENROUTER_API_KEY = OPENROUTER_API_KEY.strip()  # Убираем лишние пробелы

if not OPENROUTER_API_KEY.startswith("sk-"):
    raise ValueError(
        f"OPENROUTER_API_KEY имеет неверный формат. "
        f"Ключ должен начинаться с 'sk-'. "
        f"Текущий ключ начинается с: '{OPENROUTER_API_KEY[:10]}...'"
    )

print(f"✓ OpenRouter API ключ загружен: {OPENROUTER_API_KEY[:10]}...{OPENROUTER_API_KEY[-4:]}")


# Pydantic модели для валидации
class AnalyzeRequest(BaseModel):
    query: str
    chat_history: Optional[List[dict]] = None


class HistoryItem(BaseModel):
    query: str
    success: bool
    text_output: Optional[str] = None
    result_data: Optional[dict] = None


class AnalyzeWithHistoryRequest(BaseModel):
    query: str
    chat_history: Optional[List[HistoryItem]] = None


# Health check endpoint
@app.get("/")
async def root():
    """Проверка работы API"""
    return {
        "status": "online",
        "service": "CSV Analysis Agent API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check для мониторинга"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/analyze")
async def analyze_csv(
    file: UploadFile = File(..., description="CSV файл для анализа"),
    query: str = Form(..., description="Запрос пользователя для анализа данных"),
    chat_history: Optional[str] = Form(None, description="История чата в JSON формате")
):
    """
    Основной endpoint для анализа CSV файла

    Args:
        file: Загруженный CSV файл
        query: Запрос пользователя (например, "Построй график распределения цен")
        chat_history: JSON строка с историей предыдущих запросов (опционально)

    Returns:
        JSON с результатами анализа, включая сгенерированный код,
        текстовый результат и графики в base64
    """
    try:
        # Проверка формата файла
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Неподдерживаемый формат файла. Требуется CSV файл."
            )

        # Чтение CSV файла
        file_bytes = await file.read()

        # Парсинг истории если есть
        history = None
        if chat_history:
            import json
            try:
                history = json.loads(chat_history)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Неверный формат chat_history. Требуется валидный JSON."
                )

        # Создание агента
        agent = CSVAnalysisAgentAPI(api_key=OPENROUTER_API_KEY)

        # Загрузка CSV
        try:
            df = agent.load_csv_from_bytes(file_bytes, file.filename)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка при чтении CSV файла: {str(e)}"
            )

        # Выполнение анализа
        result = agent.analyze(query, chat_history=history)

        # Добавляем информацию о файле
        result["file_info"] = {
            "filename": file.filename,
            "size_bytes": len(file_bytes),
            "rows": df.shape[0],
            "columns": df.shape[1]
        }

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        error_detail = {
            "error": "Внутренняя ошибка сервера",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat()
        }
        return JSONResponse(
            status_code=500,
            content=error_detail
        )


@app.post("/api/schema")
async def get_csv_schema(
    file: UploadFile = File(..., description="CSV файл")
):
    """
    Получить информацию о структуре CSV файла

    Args:
        file: Загруженный CSV файл

    Returns:
        JSON со схемой данных (колонки, типы, статистика)
    """
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Неподдерживаемый формат файла. Требуется CSV файл."
            )

        file_bytes = await file.read()

        # Создание агента
        agent = CSVAnalysisAgentAPI(api_key=OPENROUTER_API_KEY)

        # Загрузка CSV
        try:
            df = agent.load_csv_from_bytes(file_bytes, file.filename)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка при чтении CSV файла: {str(e)}"
            )

        # Получение схемы
        schema_info = agent.get_schema_info()

        # Добавляем имя файла
        schema_info["filename"] = file.filename

        return JSONResponse(content=schema_info)

    except HTTPException:
        raise
    except Exception as e:
        error_detail = {
            "error": "Внутренняя ошибка сервера",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        return JSONResponse(
            status_code=500,
            content=error_detail
        )


@app.post("/api/quick-analyze")
async def quick_analyze(
    file: UploadFile = File(...),
    query: str = Form(...)
):
    """
    Упрощенный endpoint без истории (для быстрых запросов)

    Args:
        file: CSV файл
        query: Запрос пользователя

    Returns:
        Результаты анализа
    """
    return await analyze_csv(file=file, query=query, chat_history=None)


@app.post("/api/analyze-multi")
async def analyze_multiple_csv(
    files: List[UploadFile] = File(..., description="Несколько CSV файлов для анализа"),
    query: str = Form(..., description="Запрос пользователя для анализа данных"),
    chat_history: Optional[str] = Form(None, description="История чата в JSON формате")
):
    """
    Endpoint для анализа нескольких CSV файлов одновременно
    Позволяет работать с данными из разных таблиц и делать перекрестный анализ

    Args:
        files: Список загруженных CSV файлов
        query: Запрос пользователя (например, "Соедини таблицы заказов и клиентов по ID")
        chat_history: JSON строка с историей предыдущих запросов (опционально)

    Returns:
        JSON с результатами анализа
    """
    try:
        # Проверка что хотя бы один файл загружен
        if not files:
            raise HTTPException(
                status_code=400,
                detail="Необходимо загрузить хотя бы один CSV файл"
            )

        # Проверка формата всех файлов
        for file in files:
            if not file.filename.endswith('.csv'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Неподдерживаемый формат файла '{file.filename}'. Требуется CSV файл."
                )

        # Чтение всех файлов
        files_data = []
        for file in files:
            file_bytes = await file.read()
            files_data.append((file_bytes, file.filename))

        # Парсинг истории если есть
        history = None
        if chat_history:
            import json
            try:
                history = json.loads(chat_history)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Неверный формат chat_history. Требуется валидный JSON."
                )

        # Создание агента
        agent = CSVAnalysisAgentAPI(api_key=OPENROUTER_API_KEY)

        # Загрузка всех CSV файлов
        try:
            loaded_dfs = agent.load_multiple_csv(files_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка при чтении CSV файлов: {str(e)}"
            )

        # Выполнение анализа
        result = agent.analyze(query, chat_history=history)

        # Добавляем информацию о всех файлах
        result["files_info"] = {
            name: {
                "filename": name + ".csv",
                "rows": df.shape[0],
                "columns": df.shape[1],
                "column_names": list(df.columns)
            }
            for name, df in loaded_dfs.items()
        }

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        error_detail = {
            "error": "Внутренняя ошибка сервера",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat()
        }
        return JSONResponse(
            status_code=500,
            content=error_detail
        )


# Запуск сервера
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"""
╔════════════════════════════════════════════════════════════╗
║         CSV Analysis Agent API Server                      ║
║         Powered by Claude Sonnet 4.5                       ║
╚════════════════════════════════════════════════════════════╝

Server starting...
- Host: {host}
- Port: {port}
- Docs: http://{host}:{port}/docs
- Health: http://{host}:{port}/health

Ready to accept requests!
    """)

    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=False,  # В продакшене должно быть False
        log_level="info"
    )
