import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4

from neo4j import Session

from app.models.relation import Relationship, RelationType

logger = logging.getLogger(__name__)

class RelationshipRepository:
    """Репозиторий для работы с отношениями CMDB"""
    
    def __init__(self, session: Session):
        """
        Инициализация репозитория отношений
        
        Args:
            session: Сессия Neo4j
        """
        self.session = session
    
    def create_relationship(
        self, 
        source_id: str, 
        target_id: str, 
        relationship_type: str,
        properties: Dict[str, Any] = None
    ) -> Optional[Relationship]:
        """
        Создать отношение между двумя сущностями
        
        Args:
            source_id: ID исходной сущности
            target_id: ID целевой сущности
            relationship_type: Тип отношения
            properties: Свойства отношения
            
        Returns:
            Созданное отношение или None в случае ошибки
        """
        try:
            # Проверяем наличие сущностей
            source_query = """
            MATCH (source {id: $source_id})
            RETURN source.type AS type
            """
            target_query = """
            MATCH (target {id: $target_id})
            RETURN target.type AS type
            """
            
            source_result = self.session.run(source_query, {"source_id": source_id})
            source_record = source_result.single()
            if not source_record:
                logger.error(f"Исходная сущность с ID {source_id} не найдена")
                return None
            
            target_result = self.session.run(target_query, {"target_id": target_id})
            target_record = target_result.single()
            if not target_record:
                logger.error(f"Целевая сущность с ID {target_id} не найдена")
                return None
            
            # Создаем ID для отношения
            relationship_id = f"REL-{uuid4().hex[:8]}"
            
            # Подготавливаем свойства отношения
            rel_properties = properties or {}
            rel_properties["id"] = relationship_id
            
            # Создаем отношение
            query = f"""
            MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
            CREATE (source)-[r:{relationship_type} $properties]->(target)
            RETURN
                $rel_id AS id,
                $rel_type AS type,
                $source_id AS source_id,
                $target_id AS target_id,
                source.type AS source_type,
                target.type AS target_type,
                properties(r) AS properties
            """
            
            result = self.session.run(
                query, 
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "properties": rel_properties,
                    "rel_id": relationship_id,
                    "rel_type": relationship_type
                }
            )
            
            record = result.single()
            if record:
                # Создаем объект Relationship
                relationship = Relationship(
                    id=record["id"],
                    type=record["type"],
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    source_type=record["source_type"],
                    target_type=record["target_type"],
                    properties=record["properties"]
                )
                return relationship
            
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании отношения: {str(e)}")
            return None
    
    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """
        Получить отношение по ID
        
        Args:
            relationship_id: ID отношения
            
        Returns:
            Отношение или None, если не найдено
        """
        try:
            query = """
            MATCH (source)-[r]->(target)
            WHERE r.id = $relationship_id
            RETURN
                r.id AS id,
                type(r) AS type,
                source.id AS source_id,
                target.id AS target_id,
                source.type AS source_type,
                target.type AS target_type,
                properties(r) AS properties
            """
            
            result = self.session.run(query, {"relationship_id": relationship_id})
            record = result.single()
            
            if record:
                # Создаем объект Relationship
                relationship = Relationship(
                    id=record["id"],
                    type=record["type"],
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    source_type=record["source_type"],
                    target_type=record["target_type"],
                    properties=record["properties"]
                )
                return relationship
            
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении отношения: {str(e)}")
            return None
    
    def update_relationship(
        self, 
        relationship_id: str, 
        properties: Dict[str, Any]
    ) -> Optional[Relationship]:
        """
        Обновить свойства отношения
        
        Args:
            relationship_id: ID отношения
            properties: Новые свойства отношения
            
        Returns:
            Обновленное отношение или None в случае ошибки
        """
        try:
            # Проверяем наличие отношения
            check_query = """
            MATCH (source)-[r]->(target)
            WHERE r.id = $relationship_id
            RETURN count(r) > 0 AS exists
            """
            
            check_result = self.session.run(check_query, {"relationship_id": relationship_id})
            check_record = check_result.single()
            
            if not check_record or not check_record["exists"]:
                logger.error(f"Отношение с ID {relationship_id} не найдено")
                return None
            
            # Обновляем свойства отношения
            # Не обновляем id и тип отношения
            properties_to_update = {k: v for k, v in properties.items() if k != "id"}
            
            # Формируем SET выражения для каждого свойства
            set_clauses = []
            for key in properties_to_update:
                set_clauses.append(f"r.{key} = ${key}")
            
            if not set_clauses:
                # Если нет свойств для обновления, просто возвращаем текущее отношение
                return self.get_relationship(relationship_id)
            
            # Добавляем обновление timestamp
            set_clauses.append("r.updated_at = datetime()")
            
            # Формируем запрос
            query = f"""
            MATCH (source)-[r]->(target)
            WHERE r.id = $relationship_id
            SET {', '.join(set_clauses)}
            RETURN
                r.id AS id,
                type(r) AS type,
                source.id AS source_id,
                target.id AS target_id,
                source.type AS source_type,
                target.type AS target_type,
                properties(r) AS properties
            """
            
            # Добавляем ID отношения к параметрам
            params = dict(properties_to_update)
            params["relationship_id"] = relationship_id
            
            result = self.session.run(query, params)
            record = result.single()
            
            if record:
                # Создаем объект Relationship
                relationship = Relationship(
                    id=record["id"],
                    type=record["type"],
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    source_type=record["source_type"],
                    target_type=record["target_type"],
                    properties=record["properties"]
                )
                return relationship
            
            return None
        except Exception as e:
            logger.error(f"Ошибка при обновлении отношения: {str(e)}")
            return None
    
    def delete_relationship(self, relationship_id: str) -> bool:
        """
        Удалить отношение
        
        Args:
            relationship_id: ID отношения
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        try:
            query = """
            MATCH (source)-[r]->(target)
            WHERE r.id = $relationship_id
            DELETE r
            RETURN count(r) AS deleted
            """
            
            result = self.session.run(query, {"relationship_id": relationship_id})
            record = result.single()
            
            return record and record["deleted"] > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении отношения: {str(e)}")
            return False
    
    def get_relationship_types(self) -> List[Dict[str, Any]]:
        """
        Получить список всех типов отношений из метаданных
        
        Returns:
            Список типов отношений с их описаниями
        """
        try:
            query = """
            MATCH (n:Metadata:RelationshipTypes)-[:HAS_RELATIONSHIP_TYPE]->(rt:RelationshipTypeDefinition)
            RETURN rt.name AS name, rt.description AS description, rt.category AS category
            ORDER BY rt.category, rt.name
            """
            
            result = self.session.run(query)
            
            # Преобразуем результаты
            relationship_types = []
            for record in result:
                relationship_types.append({
                    "name": record["name"],
                    "description": record["description"],
                    "category": record["category"]
                })
            
            return relationship_types
        except Exception as e:
            logger.error(f"Ошибка при получении типов отношений: {str(e)}")
            return []