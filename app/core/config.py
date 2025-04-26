import os
import yaml
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator

class Neo4jSettings(BaseModel):
    host: str = "localhost"
    port: int = 7687
    user: str = "neo4j"
    password: str = "656D614e+"
    database: str = "neo4j"
    
    @property
    def uri(self) -> str:
        """Получить URI для подключения к Neo4j"""
        return f"neo4j://{self.host}:{self.port}"

class APIKeySetting(BaseModel):
    client_id: str
    key: str
    permissions: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class AppSettings(BaseModel):
    app_name: str = "Dementor CMDB API"
    debug: bool = False
    api_prefix: str = "/api/v1"
    version: str = "0.1.0"
    api_keys: List[APIKeySetting] = Field(default_factory=list)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    
    @validator('api_keys', pre=True, always=True)
    def validate_api_keys(cls, v, values, **kwargs):
        if not v:
            # Создадим тестовый ключ, если он не указан
            return [
                APIKeySetting(
                    client_id="default",
                    key="test-api-key",
                    permissions=["read", "write"],
                    description="Default test API key"
                )
            ]
        return v

class Settings:
    """Синглтон для хранения настроек приложения"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._settings = None
        return cls._instance
    
    def load_from_file(self, config_path: str = "config.yml") -> AppSettings:
        """Загрузить настройки из YAML-файла"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            self._settings = AppSettings(**config_data)
        else:
            # Если файл не найден, используем значения по умолчанию
            self._settings = AppSettings()
        
        # Переопределяем из переменных окружения, если они есть
        self._override_from_env()
        return self._settings
        
    def _override_from_env(self):
        """Переопределить настройки из переменных окружения"""
        # Neo4j
        if os.getenv("CMDB_NEO4J_HOST"):
            self._settings.neo4j.host = os.getenv("CMDB_NEO4J_HOST")
        if os.getenv("CMDB_NEO4J_PORT"):
            self._settings.neo4j.port = int(os.getenv("CMDB_NEO4J_PORT"))
        if os.getenv("CMDB_NEO4J_USER"):
            self._settings.neo4j.user = os.getenv("CMDB_NEO4J_USER")
        if os.getenv("CMDB_NEO4J_PASSWORD"):
            self._settings.neo4j.password = os.getenv("CMDB_NEO4J_PASSWORD")
        if os.getenv("CMDB_NEO4J_DATABASE"):
            self._settings.neo4j.database = os.getenv("CMDB_NEO4J_DATABASE")
        
        # API ключи из переменных окружения (если есть)
        if os.getenv("CMDB_API_KEYS"):
            api_keys_str = os.getenv("CMDB_API_KEYS")
            api_keys = []
            for key_data in api_keys_str.split(';'):
                parts = key_data.split(':')
                if len(parts) >= 2:
                    api_key = APIKeySetting(
                        client_id=parts[0],
                        key=parts[1],
                        permissions=parts[2].split(',') if len(parts) > 2 else ["read"]
                    )
                    api_keys.append(api_key)
            if api_keys:
                self._settings.api_keys = api_keys
    
    @property
    def settings(self) -> AppSettings:
        """Получить настройки приложения"""
        if self._settings is None:
            self.load_from_file()
        return self._settings

# Создаем синглтон для доступа к настройкам
settings = Settings()
