import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from neo4j import Session

from app.db.repositories.relation import RelationshipRepository
from app.models.relation import Relationship
from app.schemas.relation import RelationshipCreate, RelationshipUpdate

logger = logging.getLogger(__name__)

class RelationshipService:
    """Сервис для работы с отношениями CMDB"""
    
    def __init__(self, session: Session):
        """
        Инициализация сервиса отношений
        
        Args:
            session: Сессия Neo4j
        """
        self.session = session
        self.repository = RelationshipRepository(session)
    
    def get_relationship_by_id(self, relationship_id: str) -> Optional[Relationship]:
        """
        Получить отношение по ID
        
        Args:
            relationship_id: ID отношения
            
        Returns:
            Отношение или None, если не найдено
        """
        return self.repository.get_relationship(relationship_id)
    
    def create_relationship(self, relationship_data: RelationshipCreate) -> Optional[Relationship]:
        """
        Создать новое отношение
        
        Args:
            relationship_data: Данные для создания отношения
            
        Returns:
            Созданное отношение или None в случае ошибки
        """
        # Преобразуем Pydantic модель в словарь
        rel_dict = relationship_data.dict(exclude_unset=True)
        
        # Извлекаем основные параметры
        source_id = rel_dict.pop("source_id")
        target_id = rel_dict.pop("target_id")
        rel_type = str(rel_dict.pop("type"))
        properties = rel_dict
        
        # Создаем отношение через репозиторий
        return self.repository.create_relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel_type,
            properties=properties
        )
    
    def update_relationship(self, relationship_id: str, relationship_data: RelationshipUpdate) -> Optional[Relationship]:
        """
        Обновить существующее отношение
        
        Args:
            relationship_id: ID отношения
            relationship_data: Данные для обновления
            
        Returns:
            Обновленное отношение или None в случае ошибки
        """
        # Преобразуем Pydantic модель в словарь, исключая None значения
        update_data = {
            k: v for k, v in relationship_data.dict().items() 
            if v is not None
        }
        
        # Добавляем timestamp обновления
        update_data["updated_at"] = datetime.now()
        
        # Обновляем отношение через репозиторий
        return self.repository.update_relationship(relationship_id, update_data)
    
    def delete_relationship(self, relationship_id: str) -> bool:
        """
        Удалить отношение
        
        Args:
            relationship_id: ID отношения
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        return self.repository.delete_relationship(relationship_id)
    
    def get_relationships_by_entity(
        self,
        entity_id: str,
        direction: str = "both",
        relationship_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Получить отношения для сущности
        
        Args:
            entity_id: ID сущности
            direction: Направление (both, outgoing, incoming)
            relationship_type: Тип отношения (фильтр)
            limit: Количество записей на странице
            offset: Смещение для пагинации
            
        Returns:
            Словарь с отношениями и информацией о пагинации
        """
        try:
            # Строим базовый запрос в зависимости от направления
            if direction == "outgoing":
                match_clause = f"MATCH (source {{id: $entity_id}})-[r"
                if relationship_type:
                    match_clause += f":{relationship_type}"
                match_clause += "]->(target)"
            elif direction == "incoming":
                match_clause = f"MATCH (source)-[r"
                if relationship_type:
                    match_clause += f":{relationship_type}"
                match_clause += "]->(target {{id: $entity_id}})"
            else:  # both
                match_clause = f"MATCH (n {{id: $entity_id}})"
                if relationship_type:
                    rel_type_clause = f":{relationship_type}"
                else:
                    rel_type_clause = ""
                
                match_clause += f"""
                OPTIONAL MATCH (n)-[r1{rel_type_clause}]->(target1)
                OPTIONAL MATCH (source2)-[r2{rel_type_clause}]->(n)
                WITH collect({{r: r1, source: n, target: target1}}) + 
                     collect({{r: r2, source: source2, target: n}}) AS rels
                UNWIND rels AS rel
                WHERE rel.r IS NOT NULL
                WITH rel.r AS r, rel.source AS source, rel.target AS target
                """
            
            # Если направление не "both", продолжаем простой запрос
            if direction != "both":
                query = f"""
                {match_clause}
                RETURN 
                    r.id AS id,
                    type(r) AS type,
                    source.id AS source_id,
                    target.id AS target_id,
                    source.type AS source_type,
                    target.type AS target_type,
                    properties(r) AS properties,
                    r.created_at AS created_at,
                    r.updated_at AS updated_at
                ORDER BY r.created_at DESC
                SKIP $offset
                LIMIT $limit
                """
            else:
                # Для направления "both" используем подготовленные переменные
                query = f"""
                RETURN 
                    r.id AS id,
                    type(r) AS type,
                    source.id AS source_id,
                    target.id AS target_id,
                    source.type AS source_type,
                    target.type AS target_type,
                    properties(r) AS properties,
                    r.created_at AS created_at,
                    r.updated_at AS updated_at
                ORDER BY r.created_at DESC
                SKIP $offset
                LIMIT $limit
                """
            
            # Выполняем запрос
            result = self.session.run(
                query, 
                {"entity_id": entity_id, "offset": offset, "limit": limit}
            )
            
            # Преобразуем результаты в список отношений
            relationships = []
            for record in result:
                # Создаем объект Relationship
                rel = Relationship(
                    id=record["id"],
                    type=record["type"],
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    source_type=record["source_type"],
                    target_type=record["target_type"],
                    properties=record["properties"],
                    created_at=record["created_at"],
                    updated_at=record["updated_at"]
                )
                relationships.append(rel)
            
            # Выполняем запрос подсчета
            count_query = f"""
            {match_clause}
            RETURN count(r) AS total
            """
            
            if direction == "both":
                count_query = f"""
                MATCH (n {{id: $entity_id}})
                OPTIONAL MATCH (n)-[r1{rel_type_clause}]->(target1)
                OPTIONAL MATCH (source2)-[r2{rel_type_clause}]->(n)
                WITH collect(r1) + collect(r2) AS rels
                RETURN size([r IN rels WHERE r IS NOT NULL]) AS total
                """
            
            count_result = self.session.run(count_query, {"entity_id": entity_id})
            total = count_result.single()["total"]
            
            # Формируем информацию о пагинации
            page = offset // limit + 1 if offset % limit == 0 else offset // limit + 1
            total_pages = (total + limit - 1) // limit if limit > 0 else 1
            
            return {
                "items": relationships,
                "total": total,
                "page": page,
                "size": limit,
                "pages": total_pages
            }
        except Exception as e:
            logger.error(f"Ошибка при получении отношений для сущности {entity_id}: {str(e)}")
            return {
                "items": [],
                "total": 0,
                "page": 1,
                "size": limit,
                "pages": 0
            }
    
    def get_relationship_types(self) -> Dict[str, Any]:
        """
        Получить список всех типов отношений из метаданных
        
        Returns:
            Словарь с типами отношений и информацией о них
        """
        relationship_types = self.repository.get_relationship_types()
        return {
            "items": relationship_types,
            "total": len(relationship_types)
        }
    
    def bulk_create_relationships(self, relationships_data: List[RelationshipCreate]) -> List[Relationship]:
        """
        Массовое создание отношений
        
        Args:
            relationships_data: Список данных для создания отношений
            
        Returns:
            Список созданных отношений
        """
        created_relationships = []
        for rel_data in relationships_data:
            relationship = self.create_relationship(rel_data)
            if relationship:
                created_relationships.append(relationship)
        
        return created_relationships
    
    def bulk_delete_relationships(self, relationship_ids: List[str]) -> Dict[str, Any]:
        """
        Массовое удаление отношений
        
        Args:
            relationship_ids: Список ID отношений для удаления
            
        Returns:
            Словарь с информацией о результатах удаления
        """
        success_count = 0
        failed_ids = []
        
        for rel_id in relationship_ids:
            if self.delete_relationship(rel_id):
                success_count += 1
            else:
                failed_ids.append(rel_id)
        
        return {
            "total": len(relationship_ids),
            "success": success_count,
            "failed": len(failed_ids),
            "failed_ids": failed_ids
        }