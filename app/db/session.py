import logging
from typing import Optional, Generator, Dict, Any
import os

from neo4j import GraphDatabase, Session, Driver, Result
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.core.config import settings

logger = logging.getLogger(__name__)

class Neo4jSessionManager:
    """Менеджер сессий Neo4j"""
    
    _instance: Optional['Neo4jSessionManager'] = None
    _driver: Optional[Driver] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jSessionManager, cls).__new__(cls)
            cls._instance._initialize_driver()
        return cls._instance
    
    def _initialize_driver(self) -> None:
        """Инициализировать драйвер Neo4j"""
        neo4j_config = settings.settings.neo4j
        try:
            # Используем bolt:// вместо neo4j:// для одиночной инсталляции Neo4j
            uri = f"bolt://{neo4j_config.host}:{neo4j_config.port}"
            logger.info(f"Попытка подключения к Neo4j по URI: {uri}")
            
            self._driver = GraphDatabase.driver(
                uri,
                auth=(neo4j_config.user, neo4j_config.password),
                connection_timeout=5  # Добавляем таймаут подключения для предотвращения зависаний
            )
            
            # Проверяем соединение
            with self._driver.session(database=neo4j_config.database) as session:
                result = session.run("RETURN 1 AS test")
                if result.single()["test"] == 1:
                    logger.info(f"Успешное подключение к Neo4j: {uri}")
                else:
                    logger.error("Некорректный ответ при проверке подключения к Neo4j")
                    self._driver = None
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Ошибка подключения к Neo4j: {str(e)}")
            self._driver = None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при подключении к Neo4j: {str(e)}")
            self._driver = None
    
    def get_session(self) -> Session:
        """Получить сессию Neo4j"""
        if not self._driver:
            self._initialize_driver()
            if not self._driver:
                raise Exception("Не удалось подключиться к Neo4j")
        
        return self._driver.session(database=settings.settings.neo4j.database)
    
    def close(self) -> None:
        """Закрыть драйвер Neo4j"""
        if self._driver:
            self._driver.close()
            self._driver = None
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> Result:
        """Выполнить запрос Cypher"""
        with self.get_session() as session:
            result = session.run(query, params or {})
            return result
    
    def check_connection(self) -> bool:
        """Проверить соединение с Neo4j"""
        try:
            with self.get_session() as session:
                result = session.run("RETURN 1 AS test")
                return result.single()["test"] == 1
        except Exception as e:
            logger.error(f"Ошибка проверки соединения с Neo4j: {str(e)}")
            return False

# Создаем синглтон для доступа к сессиям Neo4j
neo4j_manager = Neo4jSessionManager()

def get_neo4j_session() -> Generator[Session, None, None]:
    """Генератор для получения сессии Neo4j"""
    session = neo4j_manager.get_session()
    try:
        yield session
    finally:
        session.close()
