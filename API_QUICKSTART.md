# API Quick Start - Быстрый старт

Быстрое руководство по запуску CSV Analysis Agent API.

---

## За 10 минут до первого запроса

### Локальный запуск (для тестирования)

```bash
# 1. Клонировать репозиторий
git clone <your-repo-url>
cd Claude_code

# 2. Установить зависимости
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_api.txt

# 3. Настроить .env
echo "OPENROUTER_API_KEY=your_key_here" > .env

# 4. Запустить сервер
python api_server.py
```

Сервер запустится на `http://localhost:8000`

### Проверка работы

```bash
# Health check
curl http://localhost:8000/health

# Тестовый анализ
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@example_sales.csv" \
  -F "query=Какая средняя цена?"
```

---

## Деплой на сервер Ubuntu

### Автоматическая установка

```bash
# Подключитесь к серверу
ssh user@your-server

# Скачайте и запустите скрипт установки
git clone <your-repo-url>
cd Claude_code

# Установка зависимостей
./setup.sh

# Настройка .env
nano .env
# Добавьте: OPENROUTER_API_KEY=your_key

# Создание и запуск службы
sudo cp csvagent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start csvagent
sudo systemctl enable csvagent

# Настройка Nginx
sudo cp nginx_csvagent.conf /etc/nginx/sites-available/csvagent
sudo ln -s /etc/nginx/sites-available/csvagent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# SSL сертификат (если есть домен)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

**Готово!** API доступен на `https://your-domain.com`

---

## Базовые примеры использования

### cURL

```bash
# Анализ CSV
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@data.csv" \
  -F "query=Построй график распределения цен"

# С историей
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@data.csv" \
  -F "query=Теперь покажи среднее" \
  -F 'chat_history=[{"query":"Построй график","success":true}]'
```

### Python

```python
import requests

with open('data.csv', 'rb') as f:
    files = {'file': f}
    data = {'query': 'Какая средняя цена?'}

    response = requests.post(
        'http://localhost:8000/api/analyze',
        files=files,
        data=data
    )

result = response.json()
print(result['text_output'])
```

### JavaScript

```javascript
const formData = new FormData();
formData.append('file', csvFile);
formData.append('query', 'Построй график');

const response = await fetch('http://localhost:8000/api/analyze', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
```

---

## Проверка работы

```bash
# Запустить тестовый скрипт
python test_api.py

# Или указать URL сервера
python test_api.py https://your-domain.com
```

---

## Основные endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/health` | GET | Проверка работы |
| `/api/schema` | POST | Получить схему CSV |
| `/api/analyze` | POST | Анализ данных |
| `/api/quick-analyze` | POST | Быстрый анализ (без истории) |
| `/docs` | GET | Swagger документация |

---

## Управление службой (на сервере)

```bash
# Статус
sudo systemctl status csvagent

# Перезапуск
sudo systemctl restart csvagent

# Просмотр логов
sudo journalctl -u csvagent -f
sudo tail -f /var/log/csvagent/error.log
```

---

## Troubleshooting

### Сервер не запускается

```bash
# Проверить логи
sudo journalctl -u csvagent -n 50

# Проверить .env
cat .env

# Проверить порт
sudo netstat -tlnp | grep 8000
```

### 502 Bad Gateway

```bash
# Проверить статус службы
sudo systemctl status csvagent

# Перезапустить
sudo systemctl restart csvagent
sudo systemctl restart nginx
```

### CORS ошибки

Обновите `api_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Интеграция с Lovable

1. Разверните API на сервере с SSL
2. Скопируйте промпт из `LOVABLE_PROMPT.md`
3. Вставьте в Lovable для создания frontend
4. Обновите URL API в созданном приложении
5. Настройте CORS для домена Lovable

Подробнее: см. `LOVABLE_PROMPT.md`

---

## Полезные ссылки

- [Полная документация API](API_DOCUMENTATION.md)
- [Инструкции по деплою](DEPLOYMENT.md)
- [Промпт для Lovable](LOVABLE_PROMPT.md)
- [Swagger UI](http://localhost:8000/docs)

---

## Следующие шаги

1. ✅ Запустить API локально
2. ✅ Протестировать с `test_api.py`
3. ✅ Развернуть на сервере
4. ✅ Настроить SSL
5. ✅ Создать frontend с Lovable
6. ✅ Интегрировать и тестировать

**Готово к использованию!** 🎉
