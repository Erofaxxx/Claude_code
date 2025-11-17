# CSV Analysis Agent API - Advanced Version

Расширенная версия API с WebSocket, Redis сессиями и Celery очередями.

---

## 🚀 Новые возможности

### WebSocket (Real-time streaming)
- Пользователь видит прогресс анализа в реальном времени
- "Генерирую код...", "Выполняю...", "Готово!"
- Двусторонняя связь клиент-сервер

### Redis (Session management)
- Каждый пользователь имеет свою сессию
- Автоматическое сохранение истории диалога
- Временное хранение с автоматическим истечением

### Celery (Task queue)
- Асинхронная обработка запросов
- Справляется с высокой нагрузкой
- Мониторинг задач через Flower

---

## Архитектура

```
Browser ──HTTP/WebSocket──> FastAPI Server
                               │
                               ├──> Redis (Сессии)
                               │
                               └──> Celery Workers ──> Python Code Execution
```

---

## Быстрый старт

### Вариант 1: Локально (для разработки)

```bash
# 1. Установить зависимости
pip install -r requirements_advanced.txt

# 2. Запустить Redis
redis-server

# 3. Запустить Celery Worker (в отдельном терминале)
celery -A celery_config worker --loglevel=info

# 4. Запустить API Server (в отдельном терминале)
python api_server_advanced.py

# 5. Опционально - Flower для мониторинга
celery -A celery_config flower --port=5555
```

Откройте:
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Flower: http://localhost:5555

### Вариант 2: Docker (рекомендуется)

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка
docker-compose ps

# Логи
docker-compose logs -f
```

---

## Endpoints

### REST API

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/health` | GET | Health check с проверкой Redis и Celery |
| `/api/sessions` | POST | Создать сессию |
| `/api/sessions/{id}` | GET | Получить сессию |
| `/api/sessions/{id}` | DELETE | Удалить сессию |
| `/api/analyze-async` | POST | Анализ через Celery (асинхронно) |
| `/api/tasks/{id}` | GET | Статус Celery задачи |

### WebSocket

| Endpoint | Описание |
|----------|----------|
| `/ws/analyze/{session_id}` | WebSocket для real-time анализа |

---

## Примеры использования

### 1. Создание сессии

```javascript
const response = await fetch('http://localhost:8000/api/sessions', {
  method: 'POST'
});

const data = await response.json();
const sessionId = data.session_id;
console.log('Session created:', sessionId);
```

### 2. Асинхронный анализ (Celery)

```javascript
const formData = new FormData();
formData.append('file', csvFile);
formData.append('query', 'Построй график');
formData.append('session_id', sessionId);

// Отправка задачи
const response = await fetch('http://localhost:8000/api/analyze-async', {
  method: 'POST',
  body: formData
});

const { task_id } = await response.json();

// Проверка статуса
const checkStatus = async () => {
  const statusResponse = await fetch(`http://localhost:8000/api/tasks/${task_id}`);
  const status = await statusResponse.json();

  if (status.status === 'SUCCESS') {
    console.log('Result:', status.result);
  } else if (status.status === 'PROCESSING') {
    console.log('Progress:', status.meta.status);
    setTimeout(checkStatus, 1000);
  }
};

checkStatus();
```

### 3. WebSocket (Real-time)

```javascript
// Подключение
const ws = new WebSocket(`ws://localhost:8000/ws/analyze/${sessionId}`);

ws.onopen = () => {
  console.log('Connected');

  // Отправка файла и запроса
  const reader = new FileReader();
  reader.onload = (e) => {
    const base64 = e.target.result.split(',')[1];

    ws.send(JSON.stringify({
      type: 'analyze',
      file_base64: base64,
      query: 'Построй график цен'
    }));
  };
  reader.readAsDataURL(csvFile);
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'task_started':
      console.log('Task ID:', data.task_id);
      break;

    case 'progress':
      console.log('Progress:', data.meta.status);
      // Показать пользователю!
      break;

    case 'result':
      if (data.status === 'success') {
        console.log('Result:', data.result);
        // Отобразить результат и графики
      }
      break;
  }
};
```

---

## WebSocket Demo

Откройте `websocket_client_example.html` в браузере для интерактивного тестирования.

Или запустите:
```bash
python -m http.server 8080
# Откройте: http://localhost:8080/websocket_client_example.html
```

---

## Форматы данных

### WebSocket Message Types

**От клиента к серверу:**

```javascript
// Анализ
{
  "type": "analyze",
  "file_base64": "...",
  "query": "Построй график"
}

// Ping
{
  "type": "ping"
}

// Закрытие
{
  "type": "close"
}
```

**От сервера к клиенту:**

```javascript
// Подключено
{
  "type": "connected",
  "message": "WebSocket подключен",
  "session_id": "..."
}

// Задача запущена
{
  "type": "task_started",
  "task_id": "abc-123"
}

// Прогресс
{
  "type": "progress",
  "task_id": "abc-123",
  "status": "PROCESSING",
  "meta": {
    "status": "Попытка 1/3: Генерация кода...",
    "attempt": 1,
    "max_attempts": 3,
    "code": "import pandas as pd..."
  }
}

// Результат
{
  "type": "result",
  "task_id": "abc-123",
  "status": "success",
  "result": {
    "success": true,
    "final_code": "...",
    "text_output": "...",
    "plots": ["data:image/png;base64,..."],
    "attempts_count": 1
  }
}

// Ошибка
{
  "type": "error",
  "message": "..."
}
```

---

## Мониторинг

### Flower Dashboard

Откройте http://localhost:5555 для просмотра:
- Активных задач
- Истории выполнения
- Статистики workers
- Графиков производительности

### Redis

```bash
# Подключение
redis-cli

# Просмотр сессий
KEYS session:*

# Просмотр конкретной сессии
GET session:your-session-id

# Мониторинг в реальном времени
MONITOR
```

---

## Тестирование

```bash
# Автоматические тесты
python test_advanced_api.py

# Или с указанием URL
python test_advanced_api.py http://your-server:8000
```

Тесты проверят:
- ✅ Health check с Redis и Celery
- ✅ Управление сессиями
- ✅ Асинхронный анализ
- ✅ Информацию о WebSocket

---

## Деплой на Production

Полные инструкции в **ADVANCED_SETUP.md**

Краткая версия:

```bash
# 1. Установка на сервере
git clone <repo>
cd Claude_code
git checkout claude/advanced-features-websocket-redis-celery

# 2. Зависимости
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_advanced.txt

# 3. Systemd services
sudo cp csvagent-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start csvagent-celery csvagent-api

# 4. Nginx для WebSocket
sudo cp nginx-advanced.conf /etc/nginx/sites-available/
sudo nginx -t && sudo systemctl reload nginx

# 5. SSL
sudo certbot --nginx -d your-domain.com
```

---

## Переменные окружения

```env
# OpenRouter API
OPENROUTER_API_KEY=your_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Сессии
SESSION_EXPIRE_SECONDS=3600

# API
HOST=0.0.0.0
PORT=8000
```

---

## Отличия от базовой версии

| Функция | Базовая версия | Расширенная версия |
|---------|----------------|-------------------|
| **Streaming** | ❌ Нет | ✅ WebSocket real-time |
| **Сессии** | ❌ История от клиента | ✅ Автоматически в Redis |
| **Очереди** | ❌ Синхронно | ✅ Celery асинхронно |
| **Множественные пользователи** | ⚠️ Работает, но блокирует | ✅ Параллельная обработка |
| **Мониторинг** | ❌ Нет | ✅ Flower dashboard |
| **Прогресс** | ❌ Только финальный результат | ✅ Видно каждый шаг |

---

## Системные требования

### Разработка:
- Python 3.8+
- Redis
- 2GB RAM

### Production:
- Python 3.8+
- Redis
- 4GB+ RAM (зависит от нагрузки)
- Ubuntu 20.04+

---

## FAQ

**Q: Как много Celery workers нужно?**
A: Начните с 2-4, увеличивайте по необходимости. Каждый worker потребляет ~200MB RAM.

**Q: WebSocket vs REST - что использовать?**
A: WebSocket для интерактивных приложений с live updates. REST для простых интеграций.

**Q: Как масштабировать?**
A: Добавьте больше Celery workers. Redis может быть на отдельном сервере.

**Q: Безопасно ли?**
A: Код выполняется изолированно, но добавьте authentication для production.

**Q: Как долго хранятся сессии?**
A: По умолчанию 1 час, настраивается через SESSION_EXPIRE_SECONDS.

---

## Troubleshooting

См. раздел Troubleshooting в **ADVANCED_SETUP.md**

---

## Roadmap

- [ ] Authentication/Authorization
- [ ] Rate limiting per user
- [ ] Database вместо Redis для истории
- [ ] Kubernetes deployment
- [ ] Horizontal scaling
- [ ] WebRTC для больших файлов

---

## Contributing

Pull requests приветствуются!

---

## License

MIT

---

**Расширенная версия готова к production!** 🚀

Документация:
- **ADVANCED_SETUP.md** - полные инструкции по установке
- **websocket_client_example.html** - демо WebSocket
- **docker-compose.yml** - Docker деплой

Тестирование:
- **test_advanced_api.py** - автоматические тесты

Вопросы? Создайте issue в репозитории.
