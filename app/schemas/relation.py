from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

from app.models.relation import RelationType


class RelationshipBase(BaseModel):
    """Базовая модель для создания/обновления отношения"""
    source_id: str
    target_id: str
    type: RelationType
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class RelationshipCreate(RelationshipBase):
    """Модель для создания отношения"""
    id: Optional[str] = None  # Если не указан, будет сгенерирован автоматически

    @validator('id')
    def validate_id(cls, v):
        if v is not None and not v.strip():
            raise ValueError('id не может быть пустой строкой')
        return v


class RelationshipUpdate(BaseModel):
    """Модель для обновления отношения"""
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class RelationshipRead(RelationshipBase):
    """Модель для чтения отношения"""
    id: str
    source_type: str
    target_type: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class RelationshipList(BaseModel):
    """Модель для списка отношений с пагинацией"""
    items: List[RelationshipRead]
    total: int
    page: int
    size: int
    pages: int


class RelationshipTypeInfo(BaseModel):
    """Информация о типе отношения"""
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class RelationshipTypeList(BaseModel):
    """Список типов отношений"""
    items: List[RelationshipTypeInfo]
    total: int


class RelationshipBulkCreate(BaseModel):
    """Модель для массового создания отношений"""
    relationships: List[RelationshipCreate]


class RelationshipBulkDelete(BaseModel):
    """Модель для массового удаления отношений"""
    ids: List[str]


class RelationshipSearchCriteria(BaseModel):
    """Критерии поиска отношений"""
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    type: Optional[RelationType] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    property_filters: Dict[str, Any] = Field(default_factory=dict)