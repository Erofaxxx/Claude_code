# Расширенная версия API - Инструкции по настройке

Полное руководство по установке и настройке расширенной версии CSV Analysis Agent API с WebSocket, Redis и Celery.

---

## Новые возможности

### ✨ WebSocket (Real-time анализ)
- **Streaming прогресса** - пользователь видит статус в реальном времени
- **Live обновления** - "Генерирую код...", "Выполняю...", "Готово!"
- **Двусторонняя связь** - интерактивное общение

### 🗄️ Redis (Управление сессиями)
- **Сессии пользователей** - каждый пользователь имеет свою сессию
- **История диалога** - автоматическое сохранение истории
- **Временное хранение** - сессии автоматически истекают

### ⚙️ Celery (Фоновые задачи)
- **Асинхронная обработка** - запросы не блокируют сервер
- **Очередь задач** - справляется с нагрузкой
- **Мониторинг** - Flower для отслеживания задач

---

## Архитектура

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌─────────────────────┐
│  FastAPI Server     │
│  api_server_        │
│    advanced.py      │
└─────┬───────────┬───┘
      │           │
      │           └──────┐
      ▼                  ▼
┌──────────┐      ┌────────────┐
│  Redis   │◄────►│  Celery    │
│          │      │  Workers   │
└──────────┘      └────────────┘
```

---

## Часть 1: Локальная установка (для разработки)

### Шаг 1: Установка Redis

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install redis-server

# Запуск Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Проверка
redis-cli ping
# Должно вернуть: PONG
```

#### macOS:
```bash
brew install redis

# Запуск
brew services start redis

# Проверка
redis-cli ping
```

#### Windows:
Скачайте с [redis.io](https://redis.io/download) или используйте Docker (см. ниже).

### Шаг 2: Установка зависимостей Python

```bash
cd /home/user/Claude_code

# Активировать venv
source venv/bin/activate

# Установить расширенные зависимости
pip install -r requirements_advanced.txt
```

### Шаг 3: Настройка переменных окружения

Обновите `.env`:

```bash
# OpenRouter API
OPENROUTER_API_KEY=your_key_here

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Сессии
SESSION_EXPIRE_SECONDS=3600

# API Server
HOST=0.0.0.0
PORT=8000
```

### Шаг 4: Запуск компонентов

Откройте **3 терминала**:

**Терминал 1 - Redis (если еще не запущен):**
```bash
redis-server
```

**Терминал 2 - Celery Worker:**
```bash
cd /home/user/Claude_code
source venv/bin/activate

# Запуск worker
celery -A celery_config worker --loglevel=info
```

**Терминал 3 - API Server:**
```bash
cd /home/user/Claude_code
source venv/bin/activate

# Запуск сервера
python api_server_advanced.py
```

**Опционально - Терминал 4 - Flower (мониторинг):**
```bash
cd /home/user/Claude_code
source venv/bin/activate

# Запуск Flower
celery -A celery_config flower --port=5555
```

Откройте: http://localhost:5555 для мониторинга задач.

### Шаг 5: Тестирование

**Проверка health:**
```bash
curl http://localhost:8000/health
```

Должно вернуть:
```json
{
  "status": "healthy",
  "services": {
    "redis": "ok",
    "celery": "ok"
  }
}
```

**Открыть WebSocket demo:**
```bash
# Откройте в браузере
file:///home/user/Claude_code/websocket_client_example.html

# Или запустите простой HTTP сервер
python -m http.server 8080
# Откройте: http://localhost:8080/websocket_client_example.html
```

---

## Часть 2: Docker установка (рекомендуется)

### Шаг 1: Установка Docker

#### Ubuntu:
```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo apt install docker-compose

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### Шаг 2: Настройка .env

```bash
cd /home/user/Claude_code

# Создать .env если еще нет
cp .env.example .env

# Отредактировать
nano .env
```

Добавьте:
```env
OPENROUTER_API_KEY=your_key_here
REDIS_HOST=redis
REDIS_PORT=6379
```

### Шаг 3: Запуск через Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Логи
docker-compose logs -f

# Остановка
docker-compose down
```

Сервисы:
- **Redis**: localhost:6379
- **Celery Worker**: фоновый процесс
- **Flower**: http://localhost:5555

### Шаг 4: Запуск API (вне Docker или добавить в docker-compose)

```bash
source venv/bin/activate
python api_server_advanced.py
```

Или раскомментируйте секцию `api` в `docker-compose.yml` и перезапустите.

---

## Часть 3: Production деплой на Ubuntu

### Подготовка сервера

```bash
# Подключиться к серверу
ssh user@your-server

# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить зависимости
sudo apt install -y python3 python3-pip python3-venv redis-server nginx
```

### Установка приложения

```bash
# Клонировать репозиторий
git clone <your-repo-url>
cd Claude_code

# Переключиться на расширенную ветку
git checkout claude/advanced-features-websocket-redis-celery

# Создать venv и установить зависимости
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_advanced.txt

# Настроить .env
nano .env
```

### Настройка Redis

```bash
# Запустить и включить Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Проверка
redis-cli ping

# Настроить Redis (опционально)
sudo nano /etc/redis/redis.conf
# Можно настроить: maxmemory, bind, requirepass
```

### Создание systemd сервисов

**1. Celery Worker Service:**

```bash
sudo nano /etc/systemd/system/csvagent-celery.service
```

Содержимое:
```ini
[Unit]
Description=CSV Agent Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=csvagent
Group=csvagent
WorkingDirectory=/home/csvagent/Claude_code
Environment="PATH=/home/csvagent/Claude_code/venv/bin"
ExecStart=/home/csvagent/Claude_code/venv/bin/celery -A celery_config worker --loglevel=info
Restart=always
RestartSec=10

StandardOutput=append:/var/log/csvagent/celery.log
StandardError=append:/var/log/csvagent/celery_error.log

[Install]
WantedBy=multi-user.target
```

**2. API Server Service (обновленный):**

```bash
sudo nano /etc/systemd/system/csvagent-api.service
```

Содержимое:
```ini
[Unit]
Description=CSV Agent API Server (Advanced)
After=network.target redis.service csvagent-celery.service

[Service]
Type=simple
User=csvagent
Group=csvagent
WorkingDirectory=/home/csvagent/Claude_code
Environment="PATH=/home/csvagent/Claude_code/venv/bin"
ExecStart=/home/csvagent/Claude_code/venv/bin/gunicorn api_server_advanced:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 600
Restart=always
RestartSec=10

StandardOutput=append:/var/log/csvagent/api.log
StandardError=append:/var/log/csvagent/api_error.log

[Install]
WantedBy=multi-user.target
```

**3. Flower Service (опционально):**

```bash
sudo nano /etc/systemd/system/csvagent-flower.service
```

Содержимое:
```ini
[Unit]
Description=CSV Agent Flower (Celery Monitoring)
After=network.target redis.service csvagent-celery.service

[Service]
Type=simple
User=csvagent
Group=csvagent
WorkingDirectory=/home/csvagent/Claude_code
Environment="PATH=/home/csvagent/Claude_code/venv/bin"
ExecStart=/home/csvagent/Claude_code/venv/bin/celery -A celery_config flower --port=5555
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Создание логов и запуск

```bash
# Создать директории для логов
sudo mkdir -p /var/log/csvagent
sudo chown csvagent:csvagent /var/log/csvagent

# Перезагрузить systemd
sudo systemctl daemon-reload

# Запустить сервисы
sudo systemctl start csvagent-celery
sudo systemctl start csvagent-api
sudo systemctl start csvagent-flower  # опционально

# Включить автозапуск
sudo systemctl enable csvagent-celery
sudo systemctl enable csvagent-api
sudo systemctl enable csvagent-flower

# Проверить статус
sudo systemctl status csvagent-celery
sudo systemctl status csvagent-api
```

### Настройка Nginx для WebSocket

```bash
sudo nano /etc/nginx/sites-available/csvagent-advanced
```

Содержимое:
```nginx
upstream api_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    # API endpoints
    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # WebSocket endpoint
    location /ws/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 86400;  # 24 часа для WebSocket
    }

    # Flower (опционально, защитите паролем!)
    location /flower/ {
        proxy_pass http://127.0.0.1:5555;
        proxy_set_header Host $host;
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Basic auth (настройте!)
        # auth_basic "Restricted";
        # auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

Активация:
```bash
sudo ln -s /etc/nginx/sites-available/csvagent-advanced /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL сертификат

```bash
sudo certbot --nginx -d your-domain.com
```

---

## Часть 4: Использование API

### Endpoints

#### 1. Создание сессии

**HTTP:**
```bash
curl -X POST http://localhost:8000/api/sessions
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/api/sessions', {
  method: 'POST'
});
const data = await response.json();
const sessionId = data.session_id;
```

#### 2. Асинхронный анализ через Celery

**HTTP:**
```bash
curl -X POST "http://localhost:8000/api/analyze-async" \
  -F "session_id=your-session-id" \
  -F "file=@data.csv" \
  -F "query=Построй график"
```

**Ответ:**
```json
{
  "success": true,
  "task_id": "abc-123-def",
  "status": "queued"
}
```

#### 3. Проверка статуса задачи

**HTTP:**
```bash
curl http://localhost:8000/api/tasks/abc-123-def
```

**Ответ (в процессе):**
```json
{
  "task_id": "abc-123-def",
  "status": "PROCESSING",
  "meta": {
    "status": "Попытка 1/3: Генерация кода...",
    "attempt": 1
  }
}
```

**Ответ (готово):**
```json
{
  "task_id": "abc-123-def",
  "status": "SUCCESS",
  "result": {
    "success": true,
    "final_code": "...",
    "plots": ["data:image/png;base64,..."]
  }
}
```

#### 4. WebSocket анализ

**JavaScript:**
```javascript
// 1. Создать сессию
const sessionResponse = await fetch('http://localhost:8000/api/sessions', {
  method: 'POST'
});
const { session_id } = await sessionResponse.json();

// 2. Подключиться к WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/analyze/${session_id}`);

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'progress') {
    console.log('Progress:', data.meta.status);
  }

  if (data.type === 'result') {
    console.log('Result:', data.result);
  }
};

// 3. Отправить запрос на анализ
const fileReader = new FileReader();
fileReader.onload = (e) => {
  const base64 = e.target.result.split(',')[1];

  ws.send(JSON.stringify({
    type: 'analyze',
    file_base64: base64,
    query: 'Построй график цен'
  }));
};
fileReader.readAsDataURL(csvFile);
```

---

## Часть 5: Мониторинг

### Flower Dashboard

Откройте: http://your-domain.com/flower/

Здесь можно:
- Просмотреть активные задачи
- Посмотреть историю выполнения
- Мониторить workers
- Отменять задачи

### Redis мониторинг

```bash
# Подключение к Redis CLI
redis-cli

# Просмотр всех ключей
KEYS *

# Просмотр сессии
GET session:your-session-id

# Статистика
INFO stats

# Мониторинг в реальном времени
MONITOR
```

### Логи

```bash
# API логи
sudo tail -f /var/log/csvagent/api.log

# Celery логи
sudo tail -f /var/log/csvagent/celery.log

# Системные логи
sudo journalctl -u csvagent-api -f
sudo journalctl -u csvagent-celery -f
```

---

## Часть 6: Troubleshooting

### Redis не подключается

```bash
# Проверка запущен ли Redis
sudo systemctl status redis

# Проверка порта
sudo netstat -tlnp | grep 6379

# Тест подключения
redis-cli ping

# Проверка конфигурации
cat /etc/redis/redis.conf | grep bind
# Должно быть: bind 127.0.0.1
```

### Celery worker не запускается

```bash
# Проверка логов
sudo journalctl -u csvagent-celery -n 50

# Ручной запуск для отладки
cd /home/user/Claude_code
source venv/bin/activate
celery -A celery_config worker --loglevel=debug

# Проверка конфигурации
python -c "from celery_config import celery_app; print(celery_app.conf)"
```

### WebSocket не подключается

```bash
# Проверка Nginx конфигурации для WebSocket
sudo nginx -t

# Проверка портов
sudo netstat -tlnp | grep 8000

# Тест WebSocket (с wscat)
npm install -g wscat
wscat -c ws://localhost:8000/ws/analyze/test-session-id
```

### Задачи зависают

```bash
# Просмотр активных задач через Flower
# http://localhost:5555

# Или через Celery inspect
celery -A celery_config inspect active

# Отмена всех задач
celery -A celery_config purge

# Перезапуск worker
sudo systemctl restart csvagent-celery
```

---

## Часть 7: Оптимизация

### Увеличение количества Celery workers

```bash
# В csvagent-celery.service
ExecStart=/path/to/celery -A celery_config worker --loglevel=info --concurrency=8
```

### Настройка Redis для production

```bash
sudo nano /etc/redis/redis.conf
```

Рекомендуемые настройки:
```
# Память
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Безопасность
requirepass your_strong_password
bind 127.0.0.1
```

Перезапуск:
```bash
sudo systemctl restart redis
```

Обновите .env:
```
REDIS_URL=redis://:your_strong_password@localhost:6379/0
```

### Rate Limiting

Добавьте в Nginx:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20;
    # ...
}
```

---

## Резюме команд

### Локальный запуск:
```bash
# Терминал 1
redis-server

# Терминал 2
celery -A celery_config worker --loglevel=info

# Терминал 3
python api_server_advanced.py

# Терминал 4 (опционально)
celery -A celery_config flower
```

### Production запуск:
```bash
sudo systemctl start redis
sudo systemctl start csvagent-celery
sudo systemctl start csvagent-api
sudo systemctl start csvagent-flower
```

### Проверка:
```bash
curl http://localhost:8000/health
```

---

**Расширенная версия готова!** 🚀

Теперь у вас есть:
- ✅ Real-time streaming через WebSocket
- ✅ Управление сессиями через Redis
- ✅ Асинхронная обработка через Celery
- ✅ Мониторинг через Flower
- ✅ Production-ready деплой
