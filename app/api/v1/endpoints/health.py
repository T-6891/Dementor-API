from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any

from app.core.security import get_api_key, require_admin_access
from app.services.health import HealthService

router = APIRouter()
health_service = HealthService()

@router.get("/health", summary="Проверка состояния системы")
async def check_health():
    """
    Проверка базового состояния системы.
    
    Возвращает статус "healthy" или "unhealthy" и информацию о компонентах.
    
    Доступно без авторизации для систем мониторинга.
    """
    return health_service.check_health()

@router.get("/health/detailed", summary="Детальная проверка состояния системы")
async def check_detailed_health(
    client_id: str = Depends(require_admin_access),
    include_entities: bool = Query(False, description="Включить информацию о сущностях")
):
    """
    Детальная проверка состояния системы с дополнительной информацией.
    
    Требуется доступ администратора.
    
    Args:
        include_entities: Включить информацию о распределении сущностей
        
    Returns:
        Детальная информация о состоянии системы
    """
    try:
        health_data = health_service.get_detailed_health()
        
        # Если не требуется информация о сущностях, удаляем ее из ответа
        if not include_entities and "details" in health_data and "entity_distribution" in health_data["details"]:
            del health_data["details"]["entity_distribution"]
        
        return health_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении детальной информации о состоянии системы: {str(e)}")

@router.get("/version", summary="Версия API")
async def get_version():
    """
    Получение информации о версии API.
    
    Возвращает номер версии и базовую информацию о системе.
    """
    return {
        "name": "Dementor CMDB API",
        "version": "0.1.0",
        "description": "API для управления CMDB на базе Neo4j"
    }