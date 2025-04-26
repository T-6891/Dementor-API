from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from app.core.security import require_read_access, require_write_access
from app.db.session import get_neo4j_session
from app.services.entity import EntityService
from app.schemas.entity import (
    EntityCreate, EntityUpdate, EntityRead, EntityList, 
    EntityTypeInfo, EntityTypeList, ServerCreate, ApplicationCreate, 
    ITServiceCreate, PersonCreate, IncidentCreate
)

router = APIRouter()

# Базовые эндпоинты для работы с сущностями
@router.get("", response_model=EntityList, summary="Получить список сущностей")
async def get_entities(
    type: Optional[str] = Query(None, description="Тип сущности для фильтрации"),
    limit: int = Query(100, ge=1, le=1000, description="Количество записей на странице"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    client_id: str = Depends(require_read_access),
    session = Depends(get_neo4j_session)
):
    """
    Получить список сущностей с пагинацией.
    
    - **type**: Фильтр по типу сущности
    - **limit**: Количество записей на странице
    - **offset**: Смещение для пагинации
    """
    entity_service = EntityService(session)
    return entity_service.get_entities(type, limit, offset)

# Важно: специальные эндпоинты с фиксированными путями должны быть определены ДО маршрутов с параметрами
@router.get("/types", response_model=EntityTypeList, summary="Получить список типов сущностей")
async def get_entity_types(
    client_id: str = Depends(require_read_access),
    session = Depends(get_neo4j_session)
):
    """
    Получить список всех типов сущностей из метаданных.
    """
    entity_service = EntityService(session)
    return entity_service.get_entity_types()

@router.get("/search", response_model=List[EntityRead], summary="Поиск сущностей")
async def search_entities(
    q: str = Query(..., description="Поисковый запрос"),
    fields: Optional[List[str]] = Query(None, description="Поля для поиска"),
    limit: int = Query(20, ge=1, le=100, description="Максимальное количество результатов"),
    client_id: str = Depends(require_read_access),
    session = Depends(get_neo4j_session)
):
    """
    Поиск сущностей по текстовому запросу.
    
    - **q**: Поисковый запрос
    - **fields**: Список полей для поиска (по умолчанию id, name, description)
    - **limit**: Максимальное количество результатов
    """
    entity_service = EntityService(session)
    return entity_service.search_entities(q, fields, limit)

# Специализированные эндпоинты для разных типов сущностей
@router.post("/servers", response_model=EntityRead, status_code=HTTP_201_CREATED, summary="Создать сервер")
async def create_server(
    server_data: ServerCreate,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Создать новый сервер.
    
    - **server_data**: Данные для создания сервера
    """
    entity_service = EntityService(session)
    server = entity_service.create_entity(server_data)
    if not server:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Не удалось создать сервер. Проверьте входные данные."
        )
    return server

@router.post("/applications", response_model=EntityRead, status_code=HTTP_201_CREATED, summary="Создать приложение")
async def create_application(
    app_data: ApplicationCreate,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Создать новое приложение.
    
    - **app_data**: Данные для создания приложения
    """
    entity_service = EntityService(session)
    application = entity_service.create_entity(app_data)
    if not application:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Не удалось создать приложение. Проверьте входные данные."
        )
    return application

@router.post("/services", response_model=EntityRead, status_code=HTTP_201_CREATED, summary="Создать ИТ-сервис")
async def create_it_service(
    service_data: ITServiceCreate,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Создать новый ИТ-сервис.
    
    - **service_data**: Данные для создания ИТ-сервиса
    """
    entity_service = EntityService(session)
    service = entity_service.create_entity(service_data)
    if not service:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Не удалось создать ИТ-сервис. Проверьте входные данные."
        )
    return service

@router.post("/persons", response_model=EntityRead, status_code=HTTP_201_CREATED, summary="Создать запись о сотруднике")
async def create_person(
    person_data: PersonCreate,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Создать новую запись о сотруднике.
    
    - **person_data**: Данные для создания записи о сотруднике
    """
    entity_service = EntityService(session)
    person = entity_service.create_entity(person_data)
    if not person:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Не удалось создать запись о сотруднике. Проверьте входные данные."
        )
    return person

@router.post("/incidents", response_model=EntityRead, status_code=HTTP_201_CREATED, summary="Создать инцидент")
async def create_incident(
    incident_data: IncidentCreate,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Создать новый инцидент.
    
    - **incident_data**: Данные для создания инцидента
    """
    entity_service = EntityService(session)
    incident = entity_service.create_entity(incident_data)
    if not incident:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Не удалось создать инцидент. Проверьте входные данные."
        )
    return incident

# Маршруты с параметрами должны идти после специальных маршрутов
@router.get("/{entity_id}", response_model=EntityRead, summary="Получить сущность по ID")
async def get_entity(
    entity_id: str = Path(..., description="ID сущности"),
    client_id: str = Depends(require_read_access),
    session = Depends(get_neo4j_session)
):
    """
    Получить сущность по её ID.
    
    - **entity_id**: ID сущности
    """
    entity_service = EntityService(session)
    entity = entity_service.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Сущность с ID {entity_id} не найдена"
        )
    return entity

@router.post("", response_model=EntityRead, status_code=HTTP_201_CREATED, summary="Создать новую сущность")
async def create_entity(
    entity_data: EntityCreate,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Создать новую сущность.
    
    - **entity_data**: Данные для создания сущности
    """
    entity_service = EntityService(session)
    entity = entity_service.create_entity(entity_data)
    if not entity:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Не удалось создать сущность. Проверьте входные данные."
        )
    return entity

@router.put("/{entity_id}", response_model=EntityRead, summary="Обновить сущность")
async def update_entity(
    entity_data: EntityUpdate,
    entity_id: str = Path(..., description="ID сущности"),
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Обновить существующую сущность.
    
    - **entity_id**: ID сущности
    - **entity_data**: Данные для обновления
    """
    entity_service = EntityService(session)
    entity = entity_service.update_entity(entity_id, entity_data)
    if not entity:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Сущность с ID {entity_id} не найдена или не удалось обновить"
        )
    return entity

@router.delete("/{entity_id}", summary="Удалить сущность")
async def delete_entity(
    entity_id: str = Path(..., description="ID сущности"),
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Удалить сущность по ID.
    
    - **entity_id**: ID сущности
    """
    entity_service = EntityService(session)
    success = entity_service.delete_entity(entity_id)
    if not success:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Сущность с ID {entity_id} не найдена или не удалось удалить"
        )
    return {"status": "success", "message": f"Сущность с ID {entity_id} успешно удалена"}

@router.get("/{entity_id}/related", summary="Получить связанные сущности")
async def get_related_entities(
    entity_id: str = Path(..., description="ID сущности"),
    relationship_type: Optional[str] = Query(None, description="Тип отношения для фильтрации"),
    client_id: str = Depends(require_read_access),
    session = Depends(get_neo4j_session)
):
    """
    Получить сущности, связанные с указанной.
    
    - **entity_id**: ID сущности
    - **relationship_type**: Фильтр по типу отношения
    """
    entity_service = EntityService(session)
    related_entities = entity_service.get_related_entities(entity_id, relationship_type)
    return {"items": related_entities, "total": len(related_entities)}
