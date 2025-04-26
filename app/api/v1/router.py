from fastapi import APIRouter

from app.api.v1.endpoints import health, entity, relation

# Создаем основной роутер API
api_router = APIRouter()

# Подключаем эндпоинты
api_router.include_router(health.router, tags=["health"])
api_router.include_router(entity.router, prefix="/entities", tags=["entities"])
api_router.include_router(relation.router, prefix="/relations", tags=["relations"])