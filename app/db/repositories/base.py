import logging
import json
from typing import List, Dict, Any, Optional, TypeVar, Generic, Type
from pydantic import BaseModel

from neo4j import Session
from neo4j.exceptions import ConstraintError, CypherSyntaxError

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    """
    Базовый класс репозитория для работы с Neo4j
    
    Атрибуты:
        model_class: Класс модели данных
        node_label: Метка узла в Neo4j
    """
    
    def __init__(self, session: Session, model_class: Type[T], node_label: str):
        self.session = session
        self.model_class = model_class
        self.node_label = node_label
    
    def create(self, obj: T) -> Optional[T]:
        """
        Создать новый узел в Neo4j
        
        Args:
            obj: Экземпляр модели данных
            
        Returns:
            Созданный объект или None в случае ошибки
        """
        try:
            properties = obj.dict()
            
            # Преобразование вложенных объектов и Enum в строки
            for key, value in properties.items():
                if isinstance(value, dict):
                    properties[key] = json.dumps(value)
                elif hasattr(value, 'value'):  # для Enum
                    properties[key] = value.value
                elif isinstance(value, (list, tuple)):
                    properties[key] = json.dumps(list(value))
            
            query = f"""
            CREATE (n:{self.node_label} $properties)
            RETURN n
            """
            result = self.session.run(query, {"properties": properties})
            record = result.single()
            if record:
                return self._record_to_model(record["n"])
            return None
        except ConstraintError as e:
            logger.error(f"Ошибка ограничения при создании {self.node_label}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании {self.node_label}: {str(e)}")
            return None
    
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Получить узел по ID
        
        Args:
            entity_id: ID узла
            
        Returns:
            Объект или None, если не найден
        """
        try:
            query = f"""
            MATCH (n:{self.node_label} {{id: $id}})
            RETURN n
            """
            result = self.session.run(query, {"id": entity_id})
            record = result.single()
            if record:
                return self._record_to_model(record["n"])
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении {self.node_label} по ID: {str(e)}")
            return None
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Получить все узлы данного типа
        
        Args:
            limit: Ограничение количества результатов
            offset: Смещение для пагинации
            
        Returns:
            Список объектов
        """
        try:
            query = f"""
            MATCH (n:{self.node_label})
            RETURN n
            ORDER BY n.name
            SKIP $offset
            LIMIT $limit
            """
            result = self.session.run(query, {"limit": limit, "offset": offset})
            return [self._record_to_model(record["n"]) for record in result]
        except Exception as e:
            logger.error(f"Ошибка при получении всех {self.node_label}: {str(e)}")
            return []
    
    def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[T]:
        """
        Обновить узел по ID
        
        Args:
            entity_id: ID узла
            data: Словарь с обновляемыми полями
            
        Returns:
            Обновленный объект или None в случае ошибки
        """
        try:
            # Преобразование Enum и сложных типов в строки
            properties = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    properties[key] = json.dumps(value)
                elif hasattr(value, 'value'):  # для Enum
                    properties[key] = value.value
                elif isinstance(value, (list, tuple)):
                    properties[key] = json.dumps(list(value))
                else:
                    properties[key] = value
            
            # Построение динамического запроса обновления
            set_clause = ", ".join([f"n.{key} = ${key}" for key in properties.keys()])
            query = f"""
            MATCH (n:{self.node_label} {{id: $id}})
            SET {set_clause}
            RETURN n
            """
            
            # Добавляем ID в параметры
            params = dict(properties)
            params["id"] = entity_id
            
            result = self.session.run(query, params)
            record = result.single()
            if record:
                return self._record_to_model(record["n"])
            return None
        except Exception as e:
            logger.error(f"Ошибка при обновлении {self.node_label}: {str(e)}")
            return None
    
    def delete(self, entity_id: str) -> bool:
        """
        Удалить узел по ID
        
        Args:
            entity_id: ID узла
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        try:
            query = f"""
            MATCH (n:{self.node_label} {{id: $id}})
            DETACH DELETE n
            """
            result = self.session.run(query, {"id": entity_id})
            return result.consume().counters.nodes_deleted > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении {self.node_label}: {str(e)}")
            return False
    
    def search(self, search_text: str, fields: List[str], limit: int = 20) -> List[T]:
        """
        Поиск узлов по текстовому запросу
        
        Args:
            search_text: Текст для поиска
            fields: Список полей для поиска
            limit: Ограничение количества результатов
            
        Returns:
            Список найденных объектов
        """
        try:
            # Построение WHERE условия для поиска по нескольким полям
            where_clauses = []
            params = {"search_text": f"(?i).*{search_text}.*"}
            
            for field in fields:
                where_clauses.append(f"n.{field} =~ $search_text")
            
            where_clause = " OR ".join(where_clauses)
            
            query = f"""
            MATCH (n:{self.node_label})
            WHERE {where_clause}
            RETURN n
            LIMIT $limit
            """
            
            result = self.session.run(query, {"search_text": params["search_text"], "limit": limit})
            return [self._record_to_model(record["n"]) for record in result]
        except CypherSyntaxError as e:
            logger.error(f"Ошибка синтаксиса Cypher при поиске {self.node_label}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при поиске {self.node_label}: {str(e)}")
            return []
    
    def count(self) -> int:
        """
        Подсчет количества узлов данного типа
        
        Returns:
            Количество узлов
        """
        try:
            query = f"""
            MATCH (n:{self.node_label})
            RETURN count(n) AS count
            """
            result = self.session.run(query)
            record = result.single()
            if record:
                return record["count"]
            return 0
        except Exception as e:
            logger.error(f"Ошибка при подсчете {self.node_label}: {str(e)}")
            return 0
    
    def _record_to_model(self, record: Dict) -> T:
        """
        Преобразование записи Neo4j в модель данных
        
        Args:
            record: Запись из Neo4j
            
        Returns:
            Экземпляр модели данных
        """
        try:
            # Получаем все свойства узла
            props = dict(record)
            
            # Обработка специальных типов Neo4j
            for key, value in props.items():
                # Обработка datetime
                if hasattr(value, 'to_native') and callable(getattr(value, 'to_native')):
                    try:
                        # Пытаемся преобразовать Neo4j DateTime в строку
                        props[key] = value.to_native().isoformat()
                    except Exception:
                        # Если не получается, преобразуем в строку
                        props[key] = str(value)
                
                # Обработка properties (должен быть словарь)
                if key == 'properties' and isinstance(value, str):
                    try:
                        props[key] = json.loads(value)
                    except Exception:
                        props[key] = {}
                
                # Обработка списков, хранящихся как JSON
                if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                    try:
                        props[key] = json.loads(value)
                    except Exception:
                        pass
            
            # Создаем экземпляр модели
            return self.model_class(**props)
        except Exception as e:
            logger.error(f"Ошибка при преобразовании записи в модель {self.model_class.__name__}: {str(e)}")
            # Создаем минимальную модель с обязательными полями
            try:
                # Минимальный набор полей для BaseEntity
                min_props = {
                    "id": props.get("id", "unknown"),
                    "name": props.get("name", "unknown"),
                    "type": props.get("type", "BaseEntity"),
                    "status": "Active"
                }
                return self.model_class(**min_props)
            except Exception as ex:
                logger.error(f"Не удалось создать даже минимальную модель: {str(ex)}")
                return None
