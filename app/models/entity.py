from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class EntityStatus(str, Enum):
    """Статусы сущностей"""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    MAINTENANCE = "Maintenance"
    PLANNED = "Planned"
    DECOMMISSIONED = "Decommissioned"
    DEVELOPMENT = "Development"
    TESTING = "Testing"


class EntityType(str, Enum):
    """Типы сущностей из CMDB"""
    # Организационные сущности
    ORGANIZATION = "Organization"
    DEPARTMENT = "Department"
    TEAM = "Team"
    PERSON = "Person"
    ROLE = "Role"
    
    # Инфраструктурные сущности
    LOCATION = "Location"
    BUILDING = "Building"
    ROOM = "Room"
    RACK = "Rack"
    DATA_CENTER = "DataCenter"
    
    # Аппаратные сущности
    HARDWARE_ASSET = "HardwareAsset"
    SERVER = "Server"  # Обратите внимание на изменение с "Server" на "SERVER"
    VIRTUAL_SERVER = "VirtualServer"
    NETWORK_DEVICE = "NetworkDevice"
    STORAGE_DEVICE = "StorageDevice"
    ENDPOINT = "Endpoint"
    
    # Программные сущности
    SOFTWARE_ASSET = "SoftwareAsset"
    OPERATING_SYSTEM = "OperatingSystem"
    APPLICATION = "Application"  # Изменено с "Application"
    DATABASE = "Database"
    MIDDLEWARE = "Middleware"
    SERVICE_SOFTWARE = "ServiceSoftware"
    
    # Сервисные сущности
    BUSINESS_SERVICE = "BusinessService"
    IT_SERVICE = "ITService"
    BUSINESS_PROCESS = "BusinessProcess"
    SERVICE_COMPONENT = "ServiceComponent"
    CONTRACT = "Contract"
    SLA = "SLA"
    
    # Сетевые сущности
    NETWORK = "Network"
    SUBNET = "Subnet"
    VLAN = "VLAN"
    IP_ADDRESS = "IPAddress"
    FIREWALL_RULE = "FirewallRule"
    NETWORK_SEGMENT = "NetworkSegment"
    
    # Сущности управления изменениями
    INCIDENT = "Incident"
    PROBLEM = "Problem"
    CHANGE = "Change"
    RELEASE = "Release"
    TICKET = "Ticket"
    MAINTENANCE = "Maintenance"
    
    # Сущности безопасности
    SECURITY_CONTROL = "SecurityControl"
    SECURITY_POLICY = "SecurityPolicy"
    VULNERABILITY = "Vulnerability"
    COMPLIANCE_REQUIREMENT = "ComplianceRequirement"
    ACCESS_CONTROL = "AccessControl"


class BaseEntity(BaseModel):
    """Базовая модель для всех сущностей CMDB"""
    id: str
    name: str
    type: Union[EntityType, str]
    status: EntityStatus = EntityStatus.ACTIVE
    description: Optional[str] = None
    created_at: Union[datetime, str] = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[Union[datetime, str]] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        # Разрешаем дополнительные поля для большей гибкости
        extra = "allow"
        # Разрешаем преобразование типов при валидации
        arbitrary_types_allowed = True
        # Позволяет создавать объекты из ORM данных
        from_attributes = True


class Server(BaseEntity):
    """Модель сервера"""
    type: Union[EntityType, str] = EntityType.SERVER
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    rack_id: Optional[str] = None
    
    class Config:
        # Разрешаем дополнительные поля для большей гибкости
        extra = "allow"


class Application(BaseEntity):
    """Модель приложения"""
    type: Union[EntityType, str] = EntityType.APPLICATION
    version: Optional[str] = None
    vendor: Optional[str] = None
    criticality: Optional[str] = None
    owner_id: Optional[str] = None
    
    class Config:
        # Разрешаем дополнительные поля
        extra = "allow"


class ITService(BaseEntity):
    """Модель ИТ-сервиса"""
    type: Union[EntityType, str] = EntityType.IT_SERVICE
    criticality: Optional[str] = None
    business_hours: Optional[str] = None
    owner_id: Optional[str] = None
    service_level: Optional[str] = None
    
    class Config:
        # Разрешаем дополнительные поля
        extra = "allow"


class Person(BaseEntity):
    """Модель сотрудника/пользователя"""
    type: Union[EntityType, str] = EntityType.PERSON
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[str] = None
    
    class Config:
        # Разрешаем дополнительные поля
        extra = "allow"


class Incident(BaseEntity):
    """Модель инцидента"""
    type: Union[EntityType, str] = EntityType.INCIDENT
    title: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    affected_services: List[str] = Field(default_factory=list)
    
    class Config:
        # Разрешаем дополнительные поля
        extra = "allow"
