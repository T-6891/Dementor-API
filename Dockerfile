FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Переменные среды по умолчанию
ENV CMDB_NEO4J_HOST=neo4j
ENV CMDB_NEO4J_PORT=7687
ENV CMDB_NEO4J_USER=neo4j
ENV CMDB_NEO4J_PASSWORD=password
ENV CMDB_NEO4J_DATABASE=neo4j

# Порт для приложения
EXPOSE 8000

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]