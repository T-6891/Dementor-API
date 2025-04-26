from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from app.core.security import require_read_access, require_write_access
from app.db.session import get_neo4j_session
from app.services.relation import RelationshipService
from app.schemas.relation import (
    RelationshipCreate, RelationshipUpdate, RelationshipRead, RelationshipList,
    RelationshipTypeInfo, RelationshipTypeList, RelationshipBulkCreate, RelationshipBulkDelete
)

router = APIRouter()

@router.get("", response_model=RelationshipList, summary="Получить список отношений")
async def get_relationships(
    entity_id: Optional[str] = Query(None, description="ID сущности для фильтрации"),
    direction: str = Query("both", description="Направление отношений (both, outgoing, incoming)"),
    type: Optional[str] = Query(None, description="Тип отношения для фильтрации"),
    limit: int = Query(100, ge=1, le=1000, description="Количество записей на странице"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    client_id: str = Depends(require_read_access),
    session = Depends(get_neo4j_session)
):
    """
    Получить список отношений с пагинацией.
    
    - **entity_id**: ID сущности для фильтрации (если указан)
    - **direction**: Направление отношений (both, outgoing, incoming)
    - **type**: Тип отношения для фильтрации
    - **limit**: Количество записей на странице
    - **offset**: Смещение для пагинации
    """
    relationship_service = RelationshipService(session)
    
    # Если указан ID сущности, получаем отношения для этой сущности
    if entity_id:
        return relationship_service.get_relationships_by_entity(
            entity_id=entity_id,
            direction=direction,
            relationship_type=type,
            limit=limit,
            offset=offset
        )
    
    # Иначе возвращаем ошибку, так как не реализован метод получения всех отношений
    raise HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail="Необходимо указать entity_id для получения отношений"
    )


@router.get("/{relationship_id}", response_model=RelationshipRead, summary="Получить отношение по ID")
async def get_relationship(
    relationship_id: str = Path(..., description="ID отношения"),
    client_id: str = Depends(require_read_access),
    session = Depends(get_neo4j_session)
):
    """
    Получить отношение по его ID.
    
    - **relationship_id**: ID отношения
    """
    relationship_service = RelationshipService(session)
    relationship = relationship_service.get_relationship_by_id(relationship_id)
    if not relationship:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Отношение с ID {relationship_id} не найдено"
        )
    return relationship


@router.post("", response_model=RelationshipRead, status_code=HTTP_201_CREATED, summary="Создать новое отношение")
async def create_relationship(
    relationship_data: RelationshipCreate,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Создать новое отношение между сущностями.
    
    - **relationship_data**: Данные для создания отношения
    """
    relationship_service = RelationshipService(session)
    relationship = relationship_service.create_relationship(relationship_data)
    if not relationship:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Не удалось создать отношение. Проверьте входные данные и существование сущностей."
        )
    return relationship


@router.put("/{relationship_id}", response_model=RelationshipRead, summary="Обновить отношение")
async def update_relationship(
    relationship_data: RelationshipUpdate,
    relationship_id: str = Path(..., description="ID отношения"),
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Обновить существующее отношение.
    
    - **relationship_id**: ID отношения
    - **relationship_data**: Данные для обновления
    """
    relationship_service = RelationshipService(session)
    relationship = relationship_service.update_relationship(relationship_id, relationship_data)
    if not relationship:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Отношение с ID {relationship_id} не найдено или не удалось обновить"
        )
    return relationship


@router.delete("/{relationship_id}", summary="Удалить отношение")
async def delete_relationship(
    relationship_id: str = Path(..., description="ID отношения"),
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Удалить отношение по ID.
    
    - **relationship_id**: ID отношения
    """
    relationship_service = RelationshipService(session)
    success = relationship_service.delete_relationship(relationship_id)
    if not success:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Отношение с ID {relationship_id} не найдено или не удалось удалить"
        )
    return {"status": "success", "message": f"Отношение с ID {relationship_id} успешно удалено"}


@router.get("/types", response_model=RelationshipTypeList, summary="Получить список типов отношений")
async def get_relationship_types(
    client_id: str = Depends(require_read_access),
    session = Depends(get_neo4j_session)
):
    """
    Получить список всех типов отношений из метаданных.
    """
    relationship_service = RelationshipService(session)
    return relationship_service.get_relationship_types()


@router.post("/bulk", response_model=List[RelationshipRead], status_code=HTTP_201_CREATED, summary="Массовое создание отношений")
async def bulk_create_relationships(
    data: RelationshipBulkCreate,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Массовое создание отношений между сущностями.
    
    - **data**: Список данных для создания отношений
    """
    relationship_service = RelationshipService(session)
    relationships = relationship_service.bulk_create_relationships(data.relationships)
    return relationships


@router.post("/bulk/delete", summary="Массовое удаление отношений")
async def bulk_delete_relationships(
    data: RelationshipBulkDelete,
    client_id: str = Depends(require_write_access),
    session = Depends(get_neo4j_session)
):
    """
    Массовое удаление отношений по списку ID.
    
    - **data**: Список ID отношений для удаления
    """
    relationship_service = RelationshipService(session)
    result = relationship_service.bulk_delete_relationships(data.ids)
    return result