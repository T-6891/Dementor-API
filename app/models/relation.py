from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class RelationType(str, Enum):
    """Типы отношений из CMDB"""
    # Организационные отношения
    BELONGS_TO = "BELONGS_TO"
    REPORTS_TO = "REPORTS_TO"
    MANAGES = "MANAGES"
    WORKS_IN = "WORKS_IN"
    HAS_ROLE = "HAS_ROLE"
    
    # Физические отношения
    LOCATED_IN = "LOCATED_IN"
    CONTAINS = "CONTAINS"
    ADJACENT_TO = "ADJACENT_TO"
    MOUNTED_IN = "MOUNTED_IN"
    
    # Технические отношения
    RUNS_ON = "RUNS_ON"
    CONNECTS_TO = "CONNECTS_TO"
    DEPENDS_ON = "DEPENDS_ON"
    HOSTS = "HOSTS"
    PART_OF = "PART_OF"
    INSTALLED_ON = "INSTALLED_ON"
    COMMUNICATES_WITH = "COMMUNICATES_WITH"
    
    # Сервисные отношения
    PROVIDES = "PROVIDES"
    CONSUMES = "CONSUMES"
    SUPPORTS = "SUPPORTS"
    IMPLEMENTS = "IMPLEMENTS"
    DELIVERS = "DELIVERS"
    
    # Отношения ответственности
    RESPONSIBLE_FOR = "RESPONSIBLE_FOR"
    OWNS = "OWNS"
    ASSIGNED_TO = "ASSIGNED_TO"
    SUPPORTS_L1 = "SUPPORTS_L1"
    SUPPORTS_L2 = "SUPPORTS_L2"
    SUPPORTS_L3 = "SUPPORTS_L3"
    ADMINISTERS = "ADMINISTERS"
    
    # Отношения управления изменениями
    AFFECTS = "AFFECTS"
    RESOLVES = "RESOLVES"
    RELATED_TO = "RELATED_TO"
    CAUSED_BY = "CAUSED_BY"
    REQUESTED_BY = "REQUESTED_BY"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"
    
    # Отношения безопасности
    PROTECTS = "PROTECTS"
    ENFORCES = "ENFORCES"
    COMPLIES_WITH = "COMPLIES_WITH"
    HAS_VULNERABILITY = "HAS_VULNERABILITY"
    MITIGATES = "MITIGATES"
    GRANTS_ACCESS = "GRANTS_ACCESS"
    
    # Временные отношения
    PRECEDES = "PRECEDES"
    SUCCEEDED_BY = "SUCCEEDED_BY"
    SCHEDULED_FOR = "SCHEDULED_FOR"
    VALID_FROM = "VALID_FROM"
    VALID_TO = "VALID_TO"
    
    # Бизнес-отношения
    DEFINED_IN = "DEFINED_IN"
    REFERENCED_BY = "REFERENCED_BY"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    REGULATED_BY = "REGULATED_BY"
    HAS_SLA = "HAS_SLA"


class Relationship(BaseModel):
    """Модель отношения между сущностями CMDB"""
    id: str  # Уникальный идентификатор отношения
    type: RelationType  # Тип отношения
    source_id: str  # ID исходной сущности
    target_id: str  # ID целевой сущности
    source_type: str  # Тип исходной сущности
    target_type: str  # Тип целевой сущности
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "REL-001",
                "type": "RUNS_ON",
                "source_id": "APP123456",
                "target_id": "SRV123456",
                "source_type": "Application",
                "target_type": "Server",
                "description": "Приложение работает на сервере",
                "properties": {
                    "start_date": "2023-01-01",
                    "criticality": "High"
                }
            }
        }