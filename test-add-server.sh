#!/bin/bash

# Скрипт для создания нового сервера в Dementor CMDB
# Использование: ./create_server.sh <имя сервера> <описание> <производитель> <модель>

# Значения по умолчанию
NAME=${1:-"TestServer-$(date +%s)"}
DESCRIPTION=${2:-"Тестовый сервер, созданный скриптом"}
MANUFACTURER=${3:-"Dell"}
MODEL=${4:-"PowerEdge R740"}
API_KEY=${5:-"Ui76gVkEBBLqmAjUWtAPZ8HbfkJ6F43fUgsLgaVWHPbxSMVhYKAKZwz6qZQEaG"}  # Можно передать API-ключ как параметр

# Создаем сервер через API
echo "Создаем сервер '${NAME}'..."
response=$(curl -s -X POST "http://localhost:8000/api/v1/entities" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"${NAME}\",
    \"description\": \"${DESCRIPTION}\",
    \"status\": \"Active\",
    \"type\": \"SERVER\",
    \"manufacturer\": \"${MANUFACTURER}\",
    \"model\": \"${MODEL}\",
    \"properties\": {
      \"created_by\": \"script\",
      \"creation_date\": \"$(date -Iseconds)\"
    }
  }")

# Проверяем наличие JSON-парсера jq
if command -v jq &> /dev/null; then
    # Используем jq для форматирования вывода
    echo "$response" | jq
    # Если jq доступен, также извлекаем ID для дальнейшего использования
    server_id=$(echo "$response" | jq -r '.id')
    if [ "$server_id" != "null" ]; then
        echo -e "\nСервер успешно создан с ID: ${server_id}"
    else
        echo -e "\nОшибка при создании сервера!"
    fi
else
    # Если jq не доступен, выводим как есть
    echo "$response"
fi
