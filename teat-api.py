#!/usr/bin/env python3
"""
Простой API-сервис для тестирования, не требующий Neo4j.
Используйте этот скрипт для проверки, работает ли базовый FastAPI на вашей системе.

Запуск:
    python3 test_api.py
"""

from fastapi import FastAPI, HTTPException, Header
from typing import Optional, Dict, Any
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import uuid

# Создаем экземпляр FastAPI
app = FastAPI(
    title="Dementor CMDB Test API",
    description="Тестовый API-сервис для проверки работоспособности",
    version="0.1.0"
)

# Простая модель данных для демонстрации
class Server(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    created_at: str = datetime.now().isoformat()

# Хранилище данных в памяти
servers = {}

# API-ключи (в реальной системе должны храниться в базе данных или конфиге)
API_KEYS = {
    "admin-api-key": {"permissions": ["read", "write", "admin"]},
    "user-api-key": {"permissions": ["read"]},
    "Ui76gVkEBBLqmAjUWtAPZ8HbfkJ6F43fUgsLgaVWHPbxSMVhYKAKZwz6qZQEaG": {"permissions": ["read", "write", "admin"]}
}

# Функция проверки API-ключа
def verify_api_key(x_api_key: Optional[str] = Header(None), required_permissions: list = ["read"]):
    if not x_api_key:
        raise HTTPException(status_code=403, detail="API-ключ отсутствует")
    
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=403, detail="Невалидный API-ключ")
    
    api_key_info = API_KEYS[x_api_key]
    if not all(perm in api_key_info["permissions"] for perm in required_permissions):
        raise HTTPException(status_code=403, detail="Недостаточно прав для выполнения операции")
    
    return x_api_key

# Корневой маршрут
@app.get("/")
async def root():
    return {
        "name": "Dementor CMDB Test API", 
        "message": "Тестовый API-сервис работает!",
        "timestamp": datetime.now().isoformat()
    }

# Проверка здоровья системы
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "components": {
            "api": {
                "status": "up"
            }
        }
    }

# Создание сервера
@app.post("/api/v1/servers", status_code=201)
async def create_server(server_data: dict, api_key: str = Header(..., alias="X-API-Key")):
    # Проверка API-ключа
    verify_api_key(api_key, ["write"])
    
    # Генерация уникального ID, если не указан
    if "id" not in server_data:
        server_data["id"] = f"SRV{uuid.uuid4().hex[:6]}"
    
    # Добавление сервера в хранилище
    server = Server(**server_data)
    servers[server.id] = server
    
    return server

# Получение списка серверов
@app.get("/api/v1/servers")
async def get_servers(api_key: str = Header(..., alias="X-API-Key")):
    # Проверка API-ключа
    verify_api_key(api_key, ["read"])
    
    return {"items": list(servers.values()), "total": len(servers)}

# Получение сервера по ID
@app.get("/api/v1/servers/{server_id}")
async def get_server(server_id: str, api_key: str = Header(..., alias="X-API-Key")):
    # Проверка API-ключа
    verify_api_key(api_key, ["read"])
    
    if server_id not in servers:
        raise HTTPException(status_code=404, detail=f"Сервер с ID {server_id} не найден")
    
    return servers[server_id]

# Запуск приложения
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
