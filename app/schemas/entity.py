from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

from app.models.entity import EntityStatus, EntityType


class EntityBase(BaseModel):
    """Базовая модель для создания/обновления сущности"""
    name: str
    status: EntityStatus = EntityStatus.ACTIVE
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class EntityCreate(EntityBase):
    """Модель для создания сущности"""
    type: EntityType
    id: Optional[str] = None  # Если не указан, будет сгенерирован автоматически

    @validator('id')
    def validate_id(cls, v):
        if v is not None and not v.strip():
            raise ValueError('id не может быть пустой строкой')
        return v


class EntityUpdate(EntityBase):
    """Модель для обновления сущности"""
    name: Optional[str] = None
    status: Optional[EntityStatus] = None


class EntityRead(EntityBase):
    """Модель для чтения сущности"""
    id: str
    type: EntityType
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class EntityList(BaseModel):
    """Модель для списка сущностей с пагинацией"""
    items: List[EntityRead]
    total: int
    page: int
    size: int
    pages: int


class EntityTypeInfo(BaseModel):
    """Информация о типе сущности"""
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class EntityTypeList(BaseModel):
    """Список типов сущностей"""
    items: List[EntityTypeInfo]
    total: int


class RelatedEntity(BaseModel):
    """Модель для связанной сущности"""
    entity: EntityRead
    relationship: Dict[str, Any]


class ServerCreate(EntityCreate):
    """Модель для создания сервера"""
    type: EntityType = EntityType.SERVER
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    rack_id: Optional[str] = None


class ApplicationCreate(EntityCreate):
    """Модель для создания приложения"""
    type: EntityType = EntityType.APPLICATION
    version: str
    vendor: Optional[str] = None
    criticality: Optional[str] = None
    owner_id: Optional[str] = None


class ITServiceCreate(EntityCreate):
    """Модель для создания ИТ-сервиса"""
    type: EntityType = EntityType.IT_SERVICE
    criticality: Optional[str] = None
    business_hours: Optional[str] = None
    owner_id: Optional[str] = None
    service_level: Optional[str] = None


class PersonCreate(EntityCreate):
    """Модель для создания записи о сотруднике"""
    type: EntityType = EntityType.PERSON
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[str] = None


class IncidentCreate(EntityCreate):
    """Модель для создания инцидента"""
    type: EntityType = EntityType.INCIDENT
    title: str
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    affected_services: List[str] = Field(default_factory=list)