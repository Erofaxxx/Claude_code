# Инструкция по обновлению API на сервере

## Команды для выполнения на сервере (167.99.37.111)

```bash
# 1. Подключиться к серверу
ssh root@167.99.37.111

# 2. Перейти в директорию проекта
cd /home/csvagent/Claude_code

# 3. Добавить директорию в safe для Git (если нужно)
git config --global --add safe.directory /home/csvagent/Claude_code

# 4. Получить обновления из репозитория
git pull origin claude/ai-csv-analysis-agent-011CUzRVkxApTixY8PTB45pS

# 5. Перезапустить сервис
systemctl restart csvagent

# 6. Проверить статус
systemctl status csvagent

# 7. Проверить логи (если нужно)
journalctl -u csvagent -f
```

## Что изменилось

### 1. Таблицы (DataFrame) теперь возвращаются с метаданными

**Раньше:**
```json
{
  "result_data": [
    {"State": "ALABAMA", "Year": 1992, ...},
    {"State": "ALASKA", "Year": 1993, ...}
  ]
}
```

**Теперь:**
```json
{
  "result_data": {
    "type": "dataframe",
    "data": [
      {"State": "ALABAMA", "Year": 1992, ...},
      {"State": "ALASKA", "Year": 1993, ...}
    ],
    "columns": ["State", "Year", "Salary"],
    "shape": {"rows": 5, "columns": 3},
    "dtypes": {"State": "object", "Year": "int64", "Salary": "float64"}
  }
}
```

Это позволит фронтенду правильно отображать таблицы вместо "[object Object]".

### 2. Умная обработка списков и многострочного текста

**Списки** (>3 коротких строк <150 символов) конвертируются в массивы:
```json
// Раньше:
{"result_data": "ALABAMA\nALASKA\nARIZONA\nARKANSAS"}

// Теперь:
{"result_data": ["ALABAMA", "ALASKA", "ARIZONA", "ARKANSAS"]}
```

**Многострочный текст** (длинные строки или <3 строк) сохраняется как есть:
```json
// Описание, отчет и т.д. - НЕ конвертируется
{"result_data": "Датасет содержит данные.\nПериод: 1990-2020."}
```

Изменения:
- ✅ Улучшен промпт для AI - он больше не будет генерировать `'\n'.join()`
- ✅ Бэкенд **умно** конвертирует: только списки → массивы, текст → как есть
- ✅ Фронтенд Lovable отображает списки с буллитами, текст в `<pre>`
- ✅ Логика одинаковая на бэкенде и фронтенде (>3 строк && <150 символов)
