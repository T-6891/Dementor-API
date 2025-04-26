import logging
import uuid
import re
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from neo4j import Session

from app.db.repositories.entity import EntityRepository
from app.models.entity import BaseEntity, EntityType
from app.schemas.entity import EntityCreate, EntityUpdate, ServerCreate, ApplicationCreate

logger = logging.getLogger(__name__)

class EntityService:
    """Сервис для работы с сущностями CMDB"""
    
    def __init__(self, session: Session):
        """
        Инициализация сервиса сущностей
        
        Args:
            session: Сессия Neo4j
        """
        self.session = session
        self.repository = EntityRepository(session)
    
    def get_entity_by_id(self, entity_id: str) -> Optional[BaseEntity]:
        """
        Получить сущность по ID
        
        Args:
            entity_id: ID сущности
            
        Returns:
            Сущность или None, если не найдена
        """
        return self.repository.get_by_id(entity_id)
    
    def get_entities(
        self, 
        entity_type: Optional[str] = None,
        limit: int = 100, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Получить список сущностей с пагинацией
        
        Args:
            entity_type: Тип сущности (фильтр)
            limit: Количество записей на странице
            offset: Смещение для пагинации
            
        Returns:
            Словарь с сущностями и информацией о пагинации
        """
        # Если указан тип сущности, используем репозиторий для этого типа
        if entity_type:
            repository = EntityRepository(self.session, entity_type)
            entities = repository.get_all(limit, offset)
            total = repository.count()
        else:
            entities = self.repository.get_all(limit, offset)
            total = self.repository.count()
        
        page = offset // limit + 1 if offset % limit == 0 else offset // limit + 1
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        
        return {
            "items": entities,
            "total": total,
            "page": page,
            "size": limit,
            "pages": total_pages
        }
    
    def create_entity(self, entity_data: EntityCreate) -> Optional[BaseEntity]:
        """
        Создать новую сущность
        
        Args:
            entity_data: Данные для создания сущности
            
        Returns:
            Созданная сущность или None в случае ошибки
        """
        try:
            # Преобразуем Pydantic модель в словарь
            entity_dict = entity_data.dict(exclude_none=True)
            
            # Обработка специальных типов
            if 'type' in entity_dict and hasattr(entity_dict['type'], 'value'):
                entity_dict['type'] = entity_dict['type'].value
            
            # Проверяем, это запрос от специального эндпоинта серверов?
            if isinstance(entity_data, ServerCreate) and 'type' not in entity_dict:
                entity_dict['type'] = EntityType.SERVER.value
            elif isinstance(entity_data, ApplicationCreate) and 'type' not in entity_dict:
                entity_dict['type'] = EntityType.APPLICATION.value
            
            # Если ID не указан, генерируем его
            if not entity_dict.get("id"):
                type_value = entity_dict.get("type", "BaseEntity")
                if isinstance(type_value, EntityType):
                    type_value = type_value.value
                entity_dict["id"] = self._generate_entity_id(type_value)
            
            # ИСПРАВЛЕНИЕ: Не преобразуем properties в строку JSON
            # Оставляем properties как словарь для правильной валидации
            # Если 'properties' есть и это строка (возможно JSON), пытаемся преобразовать в словарь
            if 'properties' in entity_dict and isinstance(entity_dict['properties'], str):
                try:
                    entity_dict['properties'] = json.loads(entity_dict['properties'])
                except json.JSONDecodeError:
                    # Если не удается разобрать JSON, создаем пустой словарь
                    entity_dict['properties'] = {}
            
            # Добавляем временные метки
            now = datetime.now()
            entity_dict["created_at"] = now.isoformat()  # Преобразуем в строку ISO
            entity_dict["updated_at"] = None
            
            # Создаем экземпляр BaseEntity
            entity = BaseEntity(**entity_dict)
            
            # Используем репозиторий для создания сущности
            return self.repository.create(entity)
        except Exception as e:
            logger.error(f"Ошибка при создании сущности: {str(e)}")
            return None
    
    def update_entity(self, entity_id: str, entity_data: EntityUpdate) -> Optional[BaseEntity]:
        """
        Обновить существующую сущность
        
        Args:
            entity_id: ID сущности
            entity_data: Данные для обновления
            
        Returns:
            Обновленная сущность или None в случае ошибки
        """
        # Проверяем наличие сущности
        existing_entity = self.get_entity_by_id(entity_id)
        if not existing_entity:
            logger.warning(f"Сущность с ID {entity_id} не найдена")
            return None
        
        # Преобразуем Pydantic модель в словарь, исключая None значения
        update_data = {
            k: v for k, v in entity_data.dict().items() 
            if v is not None
        }
        
        # ИСПРАВЛЕНИЕ: Оставляем properties как словарь
        # Если properties это строка, пытаемся преобразовать в словарь
        if 'properties' in update_data and isinstance(update_data['properties'], str):
            try:
                update_data['properties'] = json.loads(update_data['properties'])
            except json.JSONDecodeError:
                update_data['properties'] = {}
            
        # Добавляем timestamp обновления
        update_data["updated_at"] = datetime.now().isoformat()
        
        # Обновляем сущность через репозиторий
        return self.repository.update(entity_id, update_data)
    
    def delete_entity(self, entity_id: str) -> bool:
        """
        Удалить сущность
        
        Args:
            entity_id: ID сущности
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        return self.repository.delete(entity_id)
    
    def search_entities(self, search_text: str, fields: List[str] = None, limit: int = 20) -> List[BaseEntity]:
        """
        Поиск сущностей по текстовому запросу
        
        Args:
            search_text: Текст для поиска
            fields: Список полей для поиска (по умолчанию id, name, description)
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных сущностей
        """
        if not fields:
            fields = ["id", "name", "description"]
        
        return self.repository.search(search_text, fields, limit)
    
    def get_related_entities(self, entity_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получить связанные сущности
        
        Args:
            entity_id: ID сущности
            relationship_type: Тип отношения (фильтр)
            
        Returns:
            Список связанных сущностей с информацией о связях
        """
        return self.repository.get_related_entities(entity_id, relationship_type)
    
    def get_entity_types(self) -> Dict[str, Any]:
        """
        Получить список всех типов сущностей из метаданных
        
        Returns:
            Словарь с типами сущностей и информацией о них
        """
        entity_types = self.repository.get_entity_types()
        return {
            "items": entity_types,
            "total": len(entity_types)
        }
    
    def _generate_entity_id(self, entity_type: Union[EntityType, str]) -> str:
        """
        Генерировать ID для сущности определенного типа
        
        Args:
            entity_type: Тип сущности
            
        Returns:
            Сгенерированный ID
        """
        # Извлекаем префикс из типа сущности
        prefix = self._get_entity_prefix(entity_type)
        
        # Генерируем случайную часть ID
        random_part = str(uuid.uuid4().int)[:6].zfill(6)
        
        return f"{prefix}{random_part}"
    
    def _get_entity_prefix(self, entity_type: Union[EntityType, str]) -> str:
        """
        Получить префикс для ID сущности
        
        Args:
            entity_type: Тип сущности
            
        Returns:
            Префикс для ID
        """
        # Если получили строку, пытаемся преобразовать в EntityType
        if isinstance(entity_type, str):
            try:
                entity_type = EntityType(entity_type)
            except ValueError:
                # Если не удалось преобразовать, генерируем префикс из строки
                prefix = re.sub(r'[^A-Z]', '', entity_type.upper())[:3]
                return prefix if prefix else "ENT"
        
        # Маппинг типов сущностей на префиксы
        prefix_map = {
            EntityType.SERVER: "SRV",
            EntityType.VIRTUAL_SERVER: "VSRV",
            EntityType.APPLICATION: "APP",
            EntityType.IT_SERVICE: "SVC",
            EntityType.BUSINESS_SERVICE: "BSVC",
            EntityType.PERSON: "PERSON",
            EntityType.DEPARTMENT: "DEPT",
            EntityType.TEAM: "TEAM",
            EntityType.INCIDENT: "INC",
            EntityType.PROBLEM: "PRB",
            EntityType.CHANGE: "CHG",
            EntityType.NETWORK_DEVICE: "NET",
            EntityType.DATABASE: "DB",
            EntityType.STORAGE_DEVICE: "STG",
            EntityType.OPERATING_SYSTEM: "OS",
            EntityType.ENDPOINT: "EP",
        }
        
        # Если тип сущности есть в маппинге, возвращаем соответствующий префикс
        if entity_type in prefix_map:
            return prefix_map[entity_type]
        
        # Иначе генерируем префикс из имени типа (первые 3 буквы)
        entity_type_name = str(entity_type.name) if hasattr(entity_type, 'name') else str(entity_type)
        prefix = re.sub(r'[^A-Z]', '', entity_type_name)[:3]
        return prefix if prefix else "ENT"
