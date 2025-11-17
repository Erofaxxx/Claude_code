# CSV Analysis Agent API - Документация

Полная документация API для интеграции с frontend приложениями.

---

## Base URL

```
Production: https://your-domain.com
Development: http://localhost:8000
```

---

## Endpoints

### 1. Health Check

Проверка работоспособности API.

**Endpoint:** `GET /health`

**Параметры:** Нет

**Пример запроса:**
```bash
curl http://localhost:8000/health
```

**Пример ответа:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

**Коды ответа:**
- `200` - Сервер работает нормально

---

### 2. Root Endpoint

Информация об API.

**Endpoint:** `GET /`

**Параметры:** Нет

**Пример ответа:**
```json
{
  "status": "online",
  "service": "CSV Analysis Agent API",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

---

### 3. Get CSV Schema

Получить информацию о структуре CSV файла.

**Endpoint:** `POST /api/schema`

**Content-Type:** `multipart/form-data`

**Параметры:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| file | File | Да | CSV файл |

**Пример запроса (curl):**
```bash
curl -X POST "http://localhost:8000/api/schema" \
  -F "file=@data.csv"
```

**Пример запроса (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', csvFile);

const response = await fetch('http://localhost:8000/api/schema', {
  method: 'POST',
  body: formData
});

const data = await response.json();
```

**Пример ответа:**
```json
{
  "success": true,
  "schema": {
    "columns": ["date", "product", "price", "quantity"],
    "dtypes": {
      "date": "object",
      "product": "object",
      "price": "float64",
      "quantity": "int64"
    },
    "shape": {
      "rows": 100,
      "columns": 4
    },
    "missing_values": {
      "date": 0,
      "product": 2,
      "price": 1,
      "quantity": 0
    },
    "sample_data": [
      {
        "date": "2024-01-01",
        "product": "Laptop",
        "price": 999.99,
        "quantity": 2
      },
      // ... еще 4 записи
    ],
    "summary_stats": {
      "price": {
        "count": 99.0,
        "mean": 299.99,
        "std": 150.5,
        "min": 9.99,
        "25%": 149.99,
        "50%": 249.99,
        "75%": 399.99,
        "max": 999.99
      },
      // ... для других числовых колонок
    }
  },
  "filename": "data.csv",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

**Коды ответа:**
- `200` - Успешно
- `400` - Неверный формат файла или ошибка чтения
- `500` - Внутренняя ошибка сервера

---

### 4. Analyze CSV (основной endpoint)

Выполнить AI анализ CSV данных.

**Endpoint:** `POST /api/analyze`

**Content-Type:** `multipart/form-data`

**Параметры:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| file | File | Да | CSV файл для анализа |
| query | String | Да | Вопрос/запрос пользователя |
| chat_history | String (JSON) | Нет | История предыдущих сообщений |

**Формат chat_history:**
```json
[
  {
    "query": "Какая средняя цена?",
    "success": true,
    "text_output": "Средняя цена: 299.99",
    "result_data": {"mean": 299.99}
  },
  {
    "query": "А максимальная?",
    "success": true,
    "text_output": "Максимальная цена: 999.99",
    "result_data": {"max": 999.99}
  }
]
```

**Пример запроса (curl):**
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@data.csv" \
  -F "query=Построй график распределения цен" \
  -F "chat_history=[{\"query\":\"test\",\"success\":true}]"
```

**Пример запроса (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', csvFile);
formData.append('query', 'Построй график распределения цен');

// С историей (опционально)
const history = [
  {
    query: "Какая средняя цена?",
    success: true,
    text_output: "Средняя цена: 299.99",
    result_data: {mean: 299.99}
  }
];
formData.append('chat_history', JSON.stringify(history));

const response = await fetch('http://localhost:8000/api/analyze', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

**Пример ответа (успех):**
```json
{
  "success": true,
  "query": "Построй график распределения цен",
  "code_attempts": [
    {
      "attempt": 1,
      "code": "import matplotlib.pyplot as plt\nimport seaborn as sns\n\nplt.figure(figsize=(10, 6))\nsns.histplot(df['price'], bins=20, kde=True)\nplt.title('Распределение цен')\nplt.xlabel('Цена')\nplt.ylabel('Частота')",
      "success": true
    }
  ],
  "final_code": "import matplotlib.pyplot as plt\n...",
  "result_data": null,
  "text_output": "",
  "plots": [
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA..."
  ],
  "error": null,
  "attempts_count": 1,
  "timestamp": "2024-01-01T12:00:00.000000",
  "file_info": {
    "filename": "data.csv",
    "size_bytes": 15234,
    "rows": 100,
    "columns": 4
  }
}
```

**Пример ответа (ошибка):**
```json
{
  "success": false,
  "query": "некорректный запрос",
  "code_attempts": [
    {
      "attempt": 1,
      "code": "...",
      "success": false,
      "error": "NameError: name 'unknown_column' is not defined"
    },
    {
      "attempt": 2,
      "code": "...",
      "success": false,
      "error": "..."
    }
  ],
  "final_code": null,
  "result_data": null,
  "text_output": null,
  "plots": [],
  "error": "Не удалось выполнить код после 3 попыток",
  "error_details": "NameError: ...",
  "attempts_count": 3,
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

**Коды ответа:**
- `200` - Запрос обработан (проверьте `success` в JSON)
- `400` - Неверный формат файла или параметров
- `500` - Внутренняя ошибка сервера

---

### 5. Quick Analyze (без истории)

Упрощенный endpoint для быстрых запросов без истории.

**Endpoint:** `POST /api/quick-analyze`

**Content-Type:** `multipart/form-data`

**Параметры:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| file | File | Да | CSV файл |
| query | String | Да | Запрос пользователя |

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/api/quick-analyze" \
  -F "file=@data.csv" \
  -F "query=Покажи статистику"
```

Ответ такой же как у `/api/analyze`.

---

## Примеры использования

### Python (requests)

```python
import requests

# Анализ CSV
with open('data.csv', 'rb') as f:
    files = {'file': ('data.csv', f, 'text/csv')}
    data = {'query': 'Покажи среднюю цену'}

    response = requests.post(
        'http://localhost:8000/api/analyze',
        files=files,
        data=data
    )

result = response.json()

if result['success']:
    print(f"Код: {result['final_code']}")
    print(f"Результат: {result['text_output']}")

    # Сохранить графики
    for i, plot_base64 in enumerate(result['plots']):
        # plot_base64 формат: "data:image/png;base64,..."
        img_data = plot_base64.split(',')[1]

        import base64
        with open(f'plot_{i}.png', 'wb') as img_file:
            img_file.write(base64.b64decode(img_data))
```

### JavaScript (Fetch API)

```javascript
async function analyzeCSV(file, query, history = null) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('query', query);

  if (history) {
    formData.append('chat_history', JSON.stringify(history));
  }

  try {
    const response = await fetch('http://localhost:8000/api/analyze', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    if (result.success) {
      console.log('Код:', result.final_code);
      console.log('Результат:', result.text_output);

      // Отобразить графики
      result.plots.forEach((plotBase64, i) => {
        const img = document.createElement('img');
        img.src = plotBase64; // Уже в формате data:image/png;base64,...
        document.body.appendChild(img);
      });

      return result;
    } else {
      console.error('Ошибка анализа:', result.error);
      return null;
    }
  } catch (error) {
    console.error('Ошибка запроса:', error);
    throw error;
  }
}

// Использование
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];

analyzeCSV(file, 'Построй график цен')
  .then(result => console.log('Готово!', result));
```

### React Example

```jsx
import { useState } from 'react';

function CSVAnalyzer() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const handleAnalyze = async () => {
    if (!file || !query) return;

    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('query', query);

    if (history.length > 0) {
      formData.append('chat_history', JSON.stringify(history));
    }

    try {
      const response = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      setResult(data);

      if (data.success) {
        // Добавить в историю
        setHistory([...history, {
          query: query,
          success: data.success,
          text_output: data.text_output,
          result_data: data.result_data
        }]);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept=".csv"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ваш вопрос..."
      />

      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? 'Анализирую...' : 'Анализировать'}
      </button>

      {result && result.success && (
        <div>
          <h3>Код:</h3>
          <pre>{result.final_code}</pre>

          <h3>Результат:</h3>
          <p>{result.text_output}</p>

          {result.plots && result.plots.map((plot, i) => (
            <img key={i} src={plot} alt={`График ${i+1}`} />
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Коды ошибок

| Код | Описание | Решение |
|-----|----------|---------|
| 400 | Неверный формат файла | Используйте только CSV файлы |
| 400 | Ошибка чтения CSV | Проверьте формат CSV (кодировка, разделители) |
| 400 | Неверный формат chat_history | Проверьте JSON формат истории |
| 500 | Внутренняя ошибка сервера | Проверьте логи сервера |
| 503 | Сервис недоступен | Проверьте, запущен ли сервер |

---

## Ограничения

- **Размер файла:** До 100MB (настраивается в Nginx)
- **Timeout:** 600 секунд (10 минут)
- **Попытки исправления кода:** Максимум 3
- **Формат файла:** Только CSV
- **Кодировка:** UTF-8 (рекомендуется)

---

## CORS

API настроен на прием запросов от любых доменов (`allow_origins=["*"]`).

Для production рекомендуется ограничить:

```python
allow_origins=[
    "https://your-frontend-domain.com",
    "https://your-lovable-app.lovable.app"
]
```

---

## Rate Limiting

В базовой версии rate limiting не настроен.

Для production рекомендуется настроить через Nginx:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=api_limit burst=20;
    # ...
}
```

---

## Безопасность

### Рекомендации:

1. **HTTPS:** Всегда используйте HTTPS в production
2. **API Keys:** Рассмотрите добавление API ключей для аутентификации
3. **File Validation:** Проверяйте CSV файлы на безопасность
4. **Input Sanitization:** Валидируйте входные запросы
5. **Rate Limiting:** Ограничьте количество запросов

### Добавление API Key аутентификации:

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

@app.post("/api/analyze", dependencies=[Depends(verify_api_key)])
async def analyze_csv(...):
    # ...
```

Использование:

```javascript
fetch('http://localhost:8000/api/analyze', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key'
  },
  body: formData
})
```

---

## Swagger Documentation

API автоматически генерирует Swagger документацию.

Доступна по адресу: `http://your-domain.com/docs`

Интерактивная документация позволяет:
- Просмотреть все endpoints
- Попробовать API прямо в браузере
- Посмотреть схемы данных
- Скачать OpenAPI спецификацию

---

## Поддержка

Проблемы и вопросы: создайте issue в GitHub репозитории.

**Happy coding!** 🚀
