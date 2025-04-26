import logging
from typing import List, Dict, Any, Optional, Type, Union

from neo4j import Session

from app.db.repositories.base import BaseRepository
from app.models.entity import (
    BaseEntity, Server, Application, ITService, Person, Incident, 
    EntityType
)

logger = logging.getLogger(__name__)

class EntityRepository(BaseRepository[BaseEntity]):
    """Репозиторий для работы с сущностями CMDB"""
    
    def __init__(self, session: Session, entity_type: Optional[str] = None):
        """
        Инициализация репозитория сущностей
        
        Args:
            session: Сессия Neo4j
            entity_type: Тип сущности (если указан, будут возвращаться только сущности этого типа)
        """
        # Выбор класса модели в зависимости от типа сущности
        self.entity_type = entity_type
        
        # Определяем класс модели и метку для Neo4j
        model_class, node_label = self._get_model_info()
        
        super().__init__(session, model_class, node_label)
    
    def _get_model_info(self) -> tuple[Type[BaseEntity], str]:
        """
        Получить класс модели и метку узла в зависимости от типа сущности
        
        Returns:
            Кортеж (класс модели, метка узла)
        """
        if not self.entity_type or self.entity_type == "BaseEntity":
            return BaseEntity, "Entity"
        
        # Маппинг типов сущностей на классы моделей
        entity_map = {
            EntityType.SERVER.value: (Server, "Server"),
            EntityType.APPLICATION.value: (Application, "Application"),
            EntityType.IT_SERVICE.value: (ITService, "ITService"),
            EntityType.PERSON.value: (Person, "Person"),
            EntityType.INCIDENT.value: (Incident, "Incident"),
            # Можно добавить другие типы сущностей по мере необходимости
        }
        
        # Если указанный тип есть в маппинге, возвращаем соответствующую модель и метку
        if self.entity_type in entity_map:
            return entity_map[self.entity_type]
        
        # По умолчанию возвращаем базовую модель и метку Entity
        return BaseEntity, "Entity"
    
    def get_related_entities(self, entity_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получить связанные сущности
        
        Args:
            entity_id: ID сущности
            relationship_type: Тип отношения (если None, будут возвращены все связи)
            
        Returns:
            Список связанных сущностей с информацией о связях
        """
        try:
            # Базовый запрос
            query_parts = [
                "MATCH (n {id: $id})",
            ]
            
            # Если указан тип отношения, добавляем его в запрос
            if relationship_type:
                query_parts.append(f"-[r:{relationship_type}]->(related)")
            else:
                query_parts.append("-[r]->(related)")
            
            query_parts.append("RETURN type(r) AS relationship_type, r, related")
            
            # Собираем запрос
            query = "\n".join(query_parts)
            
            result = self.session.run(query, {"id": entity_id})
            
            # Преобразуем результаты
            related_entities = []
            for record in result:
                # Преобразуем свойства узла в словарь
                related_node = dict(record["related"])
                
                # Преобразуем свойства отношения в словарь
                relationship = dict(record["r"])
                
                # Добавляем информацию о типе отношения
                relationship_info = {
                    "type": record["relationship_type"],
                    "properties": relationship
                }
                
                related_entities.append({
                    "entity": related_node,
                    "relationship": relationship_info
                })
            
            return related_entities
        except Exception as e:
            logger.error(f"Ошибка при получении связанных сущностей: {str(e)}")
            return []
    
    def get_by_type(self, entity_type: str, limit: int = 100, offset: int = 0) -> List[BaseEntity]:
        """
        Получить сущности по типу
        
        Args:
            entity_type: Тип сущности
            limit: Ограничение количества результатов
            offset: Смещение для пагинации
            
        Returns:
            Список сущностей указанного типа
        """
        try:
            query = f"""
            MATCH (n {{type: $entity_type}})
            RETURN n
            ORDER BY n.name
            SKIP $offset
            LIMIT $limit
            """
            
            result = self.session.run(
                query, 
                {"entity_type": entity_type, "limit": limit, "offset": offset}
            )
            
            return [self._record_to_model(record["n"]) for record in result]
        except Exception as e:
            logger.error(f"Ошибка при получении сущностей по типу {entity_type}: {str(e)}")
            return []
    
    def get_entity_types(self) -> List[Dict[str, Any]]:
        """
        Получить список всех типов сущностей из метаданных
        
        Returns:
            Список типов сущностей с их описаниями
        """
        try:
            query = """
            MATCH (n:Metadata:EntityTypes)-[:HAS_ENTITY_TYPE]->(et:EntityTypeDefinition)
            RETURN et.name AS name, et.description AS description, et.category AS category
            ORDER BY et.category, et.name
            """
            
            result = self.session.run(query)
            
            # Преобразуем результаты
            entity_types = []
            for record in result:
                entity_types.append({
                    "name": record["name"],
                    "description": record["description"],
                    "category": record["category"]
                })
            
            return entity_types
        except Exception as e:
            logger.error(f"Ошибка при получении типов сущностей: {str(e)}")
            return []