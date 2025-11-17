FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование requirements
COPY requirements_advanced.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements_advanced.txt

# Копирование кода
COPY . .

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose порт
EXPOSE 8000

# Команда по умолчанию (можно переопределить в docker-compose)
CMD ["python", "api_server_advanced.py"]
