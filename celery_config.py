"""
Конфигурация Celery для фоновых задач
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Настройка Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Создание Celery приложения
celery_app = Celery(
    'csvagent',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Конфигурация Celery
celery_app.conf.update(
    # Результаты
    result_expires=3600,  # Результаты хранятся 1 час
    result_backend=REDIS_URL,

    # Сериализация
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Таймауты
    task_time_limit=600,  # 10 минут максимум на задачу
    task_soft_time_limit=540,  # 9 минут soft limit

    # Prefetch
    worker_prefetch_multiplier=1,

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Tracking
    task_track_started=True,
    task_send_sent_event=True,
)

# Автоматическое обнаружение задач
celery_app.autodiscover_tasks(['celery_tasks'])
