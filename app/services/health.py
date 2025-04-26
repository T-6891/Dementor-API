import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from app.db.session import neo4j_manager

logger = logging.getLogger(__name__)

class HealthService:
    """Сервис для проверки состояния системы"""
    
    def check_health(self) -> Dict[str, Any]:
        """
        Проверить состояние всех компонентов системы
        
        Returns:
            Словарь с информацией о состоянии компонентов
        """
        start_time = time.time()
        
        # Проверка компонентов
        neo4j_status = self._check_neo4j()
        
        # Проверка базовых данных в Neo4j
        db_status = self._check_db_data()
        
        # Формируем полный отчет
        status = {
            "status": "healthy" if neo4j_status["status"] == "up" and db_status["status"] == "ok" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",
            "components": {
                "neo4j": neo4j_status,
                "database": db_status
            },
            "response_time_ms": int((time.time() - start_time) * 1000)
        }
        
        return status
    
    def _check_neo4j(self) -> Dict[str, Any]:
        """
        Проверить подключение к Neo4j
        
        Returns:
            Словарь с информацией о состоянии Neo4j
        """
        try:
            start_time = time.time()
            connected = neo4j_manager.check_connection()
            response_time = time.time() - start_time
            
            if connected:
                return {
                    "status": "up",
                    "response_time_ms": int(response_time * 1000)
                }
            else:
                return {
                    "status": "down",
                    "error": "Не удалось подключиться к Neo4j",
                    "response_time_ms": int(response_time * 1000)
                }
        except Exception as e:
            logger.error(f"Ошибка при проверке подключения к Neo4j: {str(e)}")
            return {
                "status": "down",
                "error": str(e)
            }
    
    def _check_db_data(self) -> Dict[str, Any]:
        """
        Проверить наличие базовых данных в Neo4j
        
        Returns:
            Словарь с информацией о состоянии данных
        """
        try:
            # Проверяем наличие метаданных
            with neo4j_manager.get_session() as session:
                # Проверяем наличие метаданных для типов сущностей
                entity_types_query = """
                MATCH (n:Metadata:EntityTypes)
                RETURN count(n) AS count
                """
                entity_types_result = session.run(entity_types_query)
                entity_types_count = entity_types_result.single()["count"]
                
                # Проверяем наличие метаданных для типов отношений
                relation_types_query = """
                MATCH (n:Metadata:RelationshipTypes)
                RETURN count(n) AS count
                """
                relation_types_result = session.run(relation_types_query)
                relation_types_count = relation_types_result.single()["count"]
                
                # Проверяем наличие схем свойств
                property_schemas_query = """
                MATCH (n:Metadata:PropertySchemas)
                RETURN count(n) AS count
                """
                property_schemas_result = session.run(property_schemas_query)
                property_schemas_count = property_schemas_result.single()["count"]
                
                # Проверяем общее количество сущностей
                entities_count_query = """
                MATCH (n)
                WHERE NOT n:Metadata AND NOT n:EntityTypeDefinition AND NOT n:RelationshipTypeDefinition AND NOT n:PropertySchema AND NOT n:PropertyDefinition
                RETURN count(n) AS count
                """
                entities_count_result = session.run(entities_count_query)
                entities_count = entities_count_result.single()["count"]
                
                # Статус базы данных
                status = "ok" if entity_types_count > 0 and relation_types_count > 0 and property_schemas_count > 0 else "warning"
                
                return {
                    "status": status,
                    "metadata": {
                        "entity_types": entity_types_count,
                        "relation_types": relation_types_count,
                        "property_schemas": property_schemas_count
                    },
                    "entities_count": entities_count
                }
        except Exception as e:
            logger.error(f"Ошибка при проверке данных в Neo4j: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """
        Получить детальную информацию о состоянии системы
        
        Returns:
            Словарь с детальной информацией о состоянии системы
        """
        basic_health = self.check_health()
        
        # Дополнительные проверки для детального отчета
        neo4j_details = self._get_neo4j_details()
        entity_distribution = self._get_entity_distribution()
        
        # Расширяем базовый отчет
        detailed_health = dict(basic_health)
        detailed_health["details"] = {
            "neo4j": neo4j_details,
            "entity_distribution": entity_distribution
        }
        
        return detailed_health
    
    def _get_neo4j_details(self) -> Dict[str, Any]:
        """
        Получить детальную информацию о Neo4j
        
        Returns:
            Словарь с детальной информацией о Neo4j
        """
        try:
            with neo4j_manager.get_session() as session:
                # Получаем информацию о версии Neo4j
                version_query = "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition"
                version_result = session.run(version_query)
                version_record = version_result.single()
                
                if version_record:
                    return {
                        "name": version_record["name"],
                        "version": version_record["versions"][0],
                        "edition": version_record["edition"]
                    }
                return {
                    "error": "Не удалось получить информацию о версии Neo4j"
                }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о Neo4j: {str(e)}")
            return {
                "error": str(e)
            }
    
    def _get_entity_distribution(self) -> List[Dict[str, Any]]:
        """
        Получить распределение сущностей по типам
        
        Returns:
            Список словарей с информацией о распределении сущностей
        """
        try:
            with neo4j_manager.get_session() as session:
                # Получаем распределение сущностей по типам
                query = """
                MATCH (n)
                WHERE NOT n:Metadata AND NOT n:EntityTypeDefinition AND NOT n:RelationshipTypeDefinition AND NOT n:PropertySchema AND NOT n:PropertyDefinition
                RETURN n.type AS type, count(n) AS count
                ORDER BY count DESC
                """
                result = session.run(query)
                
                distribution = []
                for record in result:
                    if record["type"]: # Пропускаем записи без типа
                        distribution.append({
                            "type": record["type"],
                            "count": record["count"]
                        })
                
                return distribution
        except Exception as e:
            logger.error(f"Ошибка при получении распределения сущностей: {str(e)}")
            return []