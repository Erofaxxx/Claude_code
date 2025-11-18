# Инструкция по обновлению API на сервере

## Команды для выполнения на сервере (167.99.37.111)

```bash
# 1. Подключиться к серверу
ssh root@167.99.37.111

# 2. Перейти в директорию проекта
cd /home/csvagent/csv_analysis_agent

# 3. Получить обновления из репозитория
git pull origin claude/ai-csv-analysis-agent-011CUzRVkxApTixY8PTB45pS

# 4. Перезапустить сервис
sudo systemctl restart csvagent

# 5. Проверить статус
sudo systemctl status csvagent

# 6. Проверить логи (если нужно)
sudo journalctl -u csvagent -f
```

## Что изменилось

Теперь API возвращает DataFrame с метаданными:

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
