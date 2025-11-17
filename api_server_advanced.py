"""
Расширенный API сервер с WebSocket, Redis и Celery
"""

import os
import json
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import redis.asyncio as aioredis

from celery_tasks import analyze_csv_task, get_schema_task
from celery.result import AsyncResult
from celery_config import celery_app

# Загрузка переменных окружения
load_dotenv()

# Инициализация FastAPI
app = FastAPI(
    title="CSV Analysis Agent API (Advanced)",
    description="AI-powered CSV analysis with WebSocket, Redis, and Celery",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis клиент
redis_client: Optional[aioredis.Redis] = None

# Конфигурация
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
SESSION_EXPIRE_SECONDS = int(os.getenv('SESSION_EXPIRE_SECONDS', 3600))  # 1 час


# Pydantic модели
class SessionCreate(BaseModel):
    user_id: Optional[str] = None


class TaskStatus(BaseModel):
    task_id: str
    status: str
    meta: Optional[dict] = None


# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    global redis_client
    redis_client = await aioredis.from_url(
        f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        encoding="utf-8",
        decode_responses=True
    )
    print(f"✓ Redis подключен: {REDIS_HOST}:{REDIS_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    global redis_client
    if redis_client:
        await redis_client.close()
        print("✓ Redis отключен")


# Health check
@app.get("/")
async def root():
    """Информация об API"""
    return {
        "status": "online",
        "service": "CSV Analysis Agent API (Advanced)",
        "version": "2.0.0",
        "features": ["WebSocket", "Redis Sessions", "Celery Queue"],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check с проверкой зависимостей"""
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }

    # Проверка Redis
    try:
        await redis_client.ping()
        health["services"]["redis"] = "ok"
    except Exception as e:
        health["services"]["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"

    # Проверка Celery
    try:
        celery_inspect = celery_app.control.inspect()
        active = celery_inspect.active()
        health["services"]["celery"] = "ok" if active is not None else "no workers"
    except Exception as e:
        health["services"]["celery"] = f"error: {str(e)}"
        health["status"] = "degraded"

    return health


# Session endpoints
@app.post("/api/sessions")
async def create_session(session_data: SessionCreate = SessionCreate()):
    """
    Создать новую сессию пользователя

    Returns:
        session_id и информация о сессии
    """
    session_id = str(uuid.uuid4())

    session_info = {
        "session_id": session_id,
        "user_id": session_data.user_id or "anonymous",
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=SESSION_EXPIRE_SECONDS)).isoformat(),
        "chat_history": []
    }

    # Сохранить в Redis
    await redis_client.setex(
        f"session:{session_id}",
        SESSION_EXPIRE_SECONDS,
        json.dumps(session_info)
    )

    return {
        "success": True,
        "session_id": session_id,
        "expires_in": SESSION_EXPIRE_SECONDS
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Получить информацию о сессии"""
    session_data = await redis_client.get(f"session:{session_id}")

    if not session_data:
        raise HTTPException(status_code=404, detail="Сессия не найдена или истекла")

    return {
        "success": True,
        "session": json.loads(session_data)
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Удалить сессию"""
    deleted = await redis_client.delete(f"session:{session_id}")

    return {
        "success": bool(deleted),
        "message": "Сессия удалена" if deleted else "Сессия не найдена"
    }


# Celery task endpoints
@app.post("/api/analyze-async")
async def analyze_csv_async(
    session_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    query: str = Form(...)
):
    """
    Асинхронный анализ CSV через Celery

    Args:
        session_id: ID сессии (опционально)
        file: CSV файл
        query: Запрос пользователя

    Returns:
        task_id для отслеживания статуса
    """
    try:
        # Проверка формата
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Требуется CSV файл")

        # Чтение файла
        file_bytes = await file.read()

        # Получение истории из сессии
        chat_history = None
        if session_id:
            session_data = await redis_client.get(f"session:{session_id}")
            if session_data:
                session_info = json.loads(session_data)
                chat_history = session_info.get("chat_history", [])

        # Запуск Celery задачи
        task = analyze_csv_task.delay(
            file_bytes,
            query,
            chat_history
        )

        return {
            "success": True,
            "task_id": task.id,
            "status": "queued",
            "message": "Задача добавлена в очередь"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Получить статус Celery задачи

    Args:
        task_id: ID задачи

    Returns:
        Статус и результат (если готов)
    """
    task_result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task_result.state,
        "result": None,
        "meta": None
    }

    if task_result.state == 'PENDING':
        response["meta"] = {"status": "Задача в очереди..."}
    elif task_result.state == 'PROCESSING':
        response["meta"] = task_result.info
    elif task_result.state == 'SUCCESS':
        response["result"] = task_result.result
    elif task_result.state == 'FAILURE':
        response["meta"] = {"error": str(task_result.info)}

    return response


# WebSocket endpoint
@app.websocket("/ws/analyze/{session_id}")
async def websocket_analyze(websocket: WebSocket, session_id: str):
    """
    WebSocket для real-time анализа

    Args:
        websocket: WebSocket соединение
        session_id: ID сессии
    """
    await websocket.accept()

    try:
        # Проверка сессии
        session_data = await redis_client.get(f"session:{session_id}")
        if not session_data:
            await websocket.send_json({
                "type": "error",
                "message": "Сессия не найдена"
            })
            await websocket.close()
            return

        session_info = json.loads(session_data)

        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket подключен",
            "session_id": session_id
        })

        while True:
            # Получение сообщения от клиента
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "analyze":
                # Анализ через WebSocket
                file_base64 = data.get("file_base64")
                query = data.get("query")

                if not file_base64 or not query:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Требуются file_base64 и query"
                    })
                    continue

                # Декодирование файла
                import base64
                file_bytes = base64.b64decode(file_base64)

                # Запуск задачи
                chat_history = session_info.get("chat_history", [])
                task = analyze_csv_task.delay(file_bytes, query, chat_history)

                await websocket.send_json({
                    "type": "task_started",
                    "task_id": task.id
                })

                # Отслеживание прогресса
                await track_task_progress(websocket, task.id, session_id, query)

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif message_type == "close":
                break

    except WebSocketDisconnect:
        print(f"WebSocket отключен: {session_id}")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()


async def track_task_progress(websocket: WebSocket, task_id: str, session_id: str, query: str):
    """
    Отслеживание прогресса задачи и отправка обновлений через WebSocket

    Args:
        websocket: WebSocket соединение
        task_id: ID задачи Celery
        session_id: ID сессии
        query: Запрос пользователя
    """
    task_result = AsyncResult(task_id, app=celery_app)

    while not task_result.ready():
        # Отправка текущего статуса
        status_data = {
            "type": "progress",
            "task_id": task_id,
            "status": task_result.state
        }

        if task_result.state == 'PROCESSING' and task_result.info:
            status_data["meta"] = task_result.info

        await websocket.send_json(status_data)

        # Ждем 0.5 секунды перед следующей проверкой
        await asyncio.sleep(0.5)

    # Задача завершена
    if task_result.successful():
        result = task_result.result

        await websocket.send_json({
            "type": "result",
            "task_id": task_id,
            "status": "success",
            "result": result
        })

        # Обновить историю сессии
        session_data = await redis_client.get(f"session:{session_id}")
        if session_data:
            session_info = json.loads(session_data)
            session_info["chat_history"].append({
                "query": query,
                "success": result.get("success"),
                "text_output": result.get("text_output"),
                "result_data": result.get("result_data")
            })

            await redis_client.setex(
                f"session:{session_id}",
                SESSION_EXPIRE_SECONDS,
                json.dumps(session_info)
            )

    else:
        await websocket.send_json({
            "type": "result",
            "task_id": task_id,
            "status": "failure",
            "error": str(task_result.info)
        })


# Запуск сервера
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"""
╔════════════════════════════════════════════════════════════╗
║      CSV Analysis Agent API Server (Advanced)              ║
║      Features: WebSocket, Redis, Celery                    ║
╚════════════════════════════════════════════════════════════╝

Server starting...
- Host: {host}
- Port: {port}
- Docs: http://{host}:{port}/docs
- Health: http://{host}:{port}/health

Services:
- Redis: {REDIS_HOST}:{REDIS_PORT}
- Celery: enabled

Ready to accept requests!
    """)

    uvicorn.run(
        "api_server_advanced:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
