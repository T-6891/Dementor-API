#!/usr/bin/env python3
"""
Dementor CMDB API - Диагностический скрипт
-------------------------------------------
Скрипт для полной диагностики всех компонентов системы Dementor CMDB:
- Проверка доступности Neo4j и авторизации
- Проверка прав на каталоги
- Проверка доступности API-сервиса
- Проверка связей между сервисами
- Тестирование функции добавления КЕ
- Формирование заключения

Использование:
    python3 cmdb_diagnostics.py [--host HOST] [--port PORT] [--api-key API_KEY] [--neo4j-host NEO4J_HOST] [--neo4j-port NEO4J_PORT]
"""

import os
import sys
import json
import time
import socket
import logging
import argparse
import subprocess
import datetime
import re
import yaml
import requests
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

# ====================================================
# МОДУЛЬ 1: Конфигурация и настройка
# ====================================================

class Status(Enum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"

@dataclass
class CheckResult:
    status: Status
    message: str
    details: Optional[Dict[str, Any]] = None

class DiagnosticConfig:
    """Конфигурация для диагностического скрипта"""
    
    def __init__(self):
        self.api_host = "localhost"
        self.api_port = 8000
        self.api_key = "Ui76gVkEBBLqmAjUWtAPZ8HbfkJ6F43fUgsLgaVWHPbxSMVhYKAKZwz6qZQEaG"
        self.neo4j_host = "localhost"
        self.neo4j_port = 7687
        self.neo4j_http_port = 7474
        self.neo4j_user = "neo4j"
        self.neo4j_password = "656D614e+"
        self.timeout = 10
        self.verbose = False
        self.using_docker = False
        self.docker_compose_file = "docker-compose.yml"
        self.api_base_url = ""
        self.neo4j_uri = ""
    
    def load_from_args(self, args):
        """Загрузка конфигурации из аргументов командной строки"""
        if args.host:
            self.api_host = args.host
        if args.port:
            self.api_port = args.port
        if args.api_key:
            self.api_key = args.api_key
        if args.neo4j_host:
            self.neo4j_host = args.neo4j_host
        if args.neo4j_port:
            self.neo4j_port = args.neo4j_port
        if args.neo4j_user:
            self.neo4j_user = args.neo4j_user
        if args.neo4j_password:
            self.neo4j_password = args.neo4j_password
        if args.timeout:
            self.timeout = args.timeout
        if args.verbose:
            self.verbose = True
        if args.docker:
            self.using_docker = True
        if args.docker_compose_file:
            self.docker_compose_file = args.docker_compose_file
        
        # Формируем базовый URL для API и URI для Neo4j
        self.api_base_url = f"http://{self.api_host}:{self.api_port}"
        self.neo4j_uri = f"bolt://{self.neo4j_host}:{self.neo4j_port}"
        
        # Если используем Docker, обновляем хосты
        if self.using_docker:
            self._update_docker_config()
    
    def load_from_config(self, config_path):
        """Загрузка конфигурации из файла config.yml"""
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                return False
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Загружаем настройки из конфигурационного файла
            if 'neo4j' in config:
                self.neo4j_host = config['neo4j'].get('host', self.neo4j_host)
                self.neo4j_port = config['neo4j'].get('port', self.neo4j_port)
                self.neo4j_user = config['neo4j'].get('user', self.neo4j_user)
                self.neo4j_password = config['neo4j'].get('password', self.neo4j_password)
            
            # Загружаем API-ключи
            if 'api_keys' in config and config['api_keys']:
                # Выбираем первый API-ключ с правами admin
                for key_config in config['api_keys']:
                    if 'admin' in key_config.get('permissions', []):
                        self.api_key = key_config.get('key', self.api_key)
                        break
            
            return True
        except Exception as e:
            logging.error(f"Ошибка при загрузке конфигурации: {str(e)}")
            return False
    
    def _update_docker_config(self):
        """Обновление конфигурации для Docker-окружения"""
        try:
            # Считываем docker-compose файл
            with open(self.docker_compose_file, 'r') as f:
                docker_config = yaml.safe_load(f)
            
            # Получаем настройки для сервисов
            if 'services' in docker_config:
                # Настройки API
                if 'api' in docker_config['services']:
                    api_service = docker_config['services']['api']
                    if 'environment' in api_service:
                        env = {k.split('=')[0]: k.split('=')[1] for k in api_service['environment'] if '=' in k}
                        if 'CMDB_NEO4J_HOST' in env:
                            self.neo4j_host = env['CMDB_NEO4J_HOST']
                        if 'CMDB_NEO4J_PORT' in env:
                            self.neo4j_port = int(env['CMDB_NEO4J_PORT'])
                        if 'CMDB_NEO4J_USER' in env:
                            self.neo4j_user = env['CMDB_NEO4J_USER']
                        if 'CMDB_NEO4J_PASSWORD' in env:
                            self.neo4j_password = env['CMDB_NEO4J_PASSWORD']
                        if 'CMDB_API_KEYS' in env:
                            api_keys = env['CMDB_API_KEYS'].split(';')
                            for key in api_keys:
                                parts = key.split(':')
                                if len(parts) >= 3 and 'admin' in parts[2]:
                                    self.api_key = parts[1]
                                    break
                
                # В Docker Compose окружении мы используем имя сервиса Neo4j вместо localhost
                if self.neo4j_host == "localhost" and 'neo4j' in docker_config['services']:
                    self.neo4j_host = "neo4j"
                
                # Обновляем URI для Neo4j
                self.neo4j_uri = f"bolt://{self.neo4j_host}:{self.neo4j_port}"
        except Exception as e:
            logging.error(f"Ошибка при обновлении конфигурации Docker: {str(e)}")

# ====================================================
# МОДУЛЬ 2: Диагностика окружения
# ====================================================

class EnvironmentChecker:
    """Проверка окружения и зависимостей"""
    
    def __init__(self, config: DiagnosticConfig):
        self.config = config
    
    def check_python_version(self) -> CheckResult:
        """Проверка версии Python"""
        try:
            version = sys.version_info
            if version.major >= 3 and version.minor >= 10:
                return CheckResult(
                    Status.OK, 
                    f"Python версии {version.major}.{version.minor}.{version.micro} соответствует требованиям"
                )
            else:
                return CheckResult(
                    Status.WARNING, 
                    f"Версия Python {version.major}.{version.minor}.{version.micro} ниже рекомендуемой (3.10+)"
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке версии Python: {str(e)}")
    
    def check_dependencies(self) -> CheckResult:
        """Проверка установленных зависимостей"""
        try:
            # Пытаемся импортировать основные зависимости
            required_packages = ['fastapi', 'uvicorn', 'neo4j', 'pydantic', 'yaml']
            missing_packages = []
            
            for package in required_packages:
                try:
                    module = __import__(package)
                except ImportError:
                    missing_packages.append(package)
            
            if missing_packages:
                return CheckResult(
                    Status.WARNING, 
                    f"Отсутствуют некоторые зависимости: {', '.join(missing_packages)}",
                    {"missing_packages": missing_packages}
                )
            else:
                return CheckResult(Status.OK, "Все необходимые зависимости установлены")
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке зависимостей: {str(e)}")
    
    def check_docker(self) -> CheckResult:
        """Проверка наличия Docker и Docker Compose"""
        if not self.config.using_docker:
            return CheckResult(Status.SKIPPED, "Проверка Docker пропущена (не используется)")
        
        try:
            # Проверка наличия Docker
            docker_result = subprocess.run(
                ["docker", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                timeout=5
            )
            
            if docker_result.returncode != 0:
                return CheckResult(
                    Status.ERROR, 
                    "Docker не установлен или не доступен",
                    {"error": docker_result.stderr}
                )
            
            # Проверка наличия Docker Compose
            compose_result = subprocess.run(
                ["docker-compose", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                timeout=5
            )
            
            if compose_result.returncode != 0:
                return CheckResult(
                    Status.WARNING, 
                    "Docker Compose не установлен или не доступен",
                    {"error": compose_result.stderr}
                )
            
            # Проверка наличия файла docker-compose.yml
            if not os.path.exists(self.config.docker_compose_file):
                return CheckResult(
                    Status.WARNING, 
                    f"Файл {self.config.docker_compose_file} не найден"
                )
            
            return CheckResult(
                Status.OK, 
                "Docker и Docker Compose доступны",
                {
                    "docker_version": docker_result.stdout.strip(),
                    "docker_compose_version": compose_result.stdout.strip()
                }
            )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке Docker: {str(e)}")
    
    def check_file_permissions(self) -> CheckResult:
        """Проверка прав на файлы и каталоги"""
        try:
            # Список каталогов, которые нужно проверить
            directories = [
                'app',
                'app/api',
                'app/core',
                'app/db',
                'app/models',
                'app/schemas',
                'app/services',
                'app/static'
            ]
            
            # Проверяем наличие и права на каталоги
            missing_dirs = []
            permission_issues = []
            
            for directory in directories:
                if not os.path.exists(directory):
                    missing_dirs.append(directory)
                elif not os.access(directory, os.R_OK):
                    permission_issues.append(f"{directory} (нет прав на чтение)")
            
            # Проверяем наличие и права на ключевые файлы
            key_files = ['app/main.py', 'config.yml', 'requirements.txt']
            missing_files = []
            
            for file in key_files:
                if not os.path.exists(file):
                    missing_files.append(file)
                elif not os.access(file, os.R_OK):
                    permission_issues.append(f"{file} (нет прав на чтение)")
            
            # Формируем результат
            if missing_dirs or missing_files or permission_issues:
                issue_details = []
                if missing_dirs:
                    issue_details.append(f"Отсутствуют каталоги: {', '.join(missing_dirs)}")
                if missing_files:
                    issue_details.append(f"Отсутствуют файлы: {', '.join(missing_files)}")
                if permission_issues:
                    issue_details.append(f"Проблемы с правами: {', '.join(permission_issues)}")
                
                return CheckResult(
                    Status.WARNING, 
                    "Обнаружены проблемы с файловой структурой",
                    {
                        "missing_directories": missing_dirs,
                        "missing_files": missing_files,
                        "permission_issues": permission_issues
                    }
                )
            else:
                return CheckResult(Status.OK, "Файловая структура в порядке")
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке файловой структуры: {str(e)}")

# ====================================================
# МОДУЛЬ 3: Диагностика Neo4j
# ====================================================

class Neo4jChecker:
    """Проверка доступности и работоспособности Neo4j"""
    
    def __init__(self, config: DiagnosticConfig):
        self.config = config
    
    def check_neo4j_connectivity(self) -> CheckResult:
        """Проверка соединения с Neo4j по Bolt-протоколу"""
        try:
            # Проверяем доступность порта Neo4j
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            result = sock.connect_ex((self.config.neo4j_host, self.config.neo4j_port))
            sock.close()
            
            if result != 0:
                return CheckResult(
                    Status.ERROR, 
                    f"Порт Neo4j {self.config.neo4j_port} недоступен на хосте {self.config.neo4j_host}"
                )
            
            # Если порт доступен, пытаемся подключиться через neo4j-драйвер
            try:
                from neo4j import GraphDatabase
                with GraphDatabase.driver(
                    self.config.neo4j_uri, 
                    auth=(self.config.neo4j_user, self.config.neo4j_password),
                    connection_timeout=self.config.timeout
                ) as driver:
                    with driver.session() as session:
                        result = session.run("RETURN 1 AS test")
                        record = result.single()
                        if record and record["test"] == 1:
                            return CheckResult(
                                Status.OK, 
                                "Успешное подключение к Neo4j через Bolt-протокол",
                                {"uri": self.config.neo4j_uri}
                            )
                        else:
                            return CheckResult(
                                Status.ERROR, 
                                "Неожиданный ответ от Neo4j при тестовом запросе"
                            )
            except Exception as driver_error:
                return CheckResult(
                    Status.ERROR, 
                    f"Ошибка при подключении к Neo4j через драйвер: {str(driver_error)}"
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке соединения с Neo4j: {str(e)}")
    
    def check_neo4j_authentication(self) -> CheckResult:
        """Проверка аутентификации в Neo4j"""
        try:
            from neo4j import GraphDatabase
            with GraphDatabase.driver(
                self.config.neo4j_uri, 
                auth=(self.config.neo4j_user, self.config.neo4j_password),
                connection_timeout=self.config.timeout
            ) as driver:
                with driver.session() as session:
                    # Проверяем права на чтение и запись
                    try:
                        # Создаем временный узел для проверки прав на запись
                        test_id = f"TEST-{uuid.uuid4().hex[:8]}"
                        write_query = f"""
                        CREATE (n:TestNode {{id: '{test_id}', created_at: datetime()}})
                        RETURN n.id AS id
                        """
                        write_result = session.run(write_query)
                        write_record = write_result.single()
                        
                        if not write_record or write_record["id"] != test_id:
                            return CheckResult(
                                Status.ERROR, 
                                "Не удалось создать тестовый узел - проблема с правами на запись"
                            )
                        
                        # Проверяем права на чтение - ищем созданный узел
                        read_query = f"""
                        MATCH (n:TestNode {{id: '{test_id}'}})
                        RETURN n.id AS id
                        """
                        read_result = session.run(read_query)
                        read_record = read_result.single()
                        
                        if not read_record or read_record["id"] != test_id:
                            return CheckResult(
                                Status.ERROR, 
                                "Не удалось найти тестовый узел - проблема с правами на чтение"
                            )
                        
                        # Удаляем тестовый узел
                        delete_query = f"""
                        MATCH (n:TestNode {{id: '{test_id}'}})
                        DELETE n
                        """
                        session.run(delete_query)
                        
                        return CheckResult(
                            Status.OK, 
                            "Аутентификация и права доступа в Neo4j в порядке"
                        )
                    except Exception as auth_error:
                        return CheckResult(
                            Status.ERROR, 
                            f"Ошибка при проверке прав доступа в Neo4j: {str(auth_error)}"
                        )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке аутентификации в Neo4j: {str(e)}")
    
    def check_neo4j_metadata(self) -> CheckResult:
        """Проверка наличия метаданных в Neo4j"""
        try:
            from neo4j import GraphDatabase
            with GraphDatabase.driver(
                self.config.neo4j_uri, 
                auth=(self.config.neo4j_user, self.config.neo4j_password),
                connection_timeout=self.config.timeout
            ) as driver:
                with driver.session() as session:
                    # Проверяем наличие метаданных
                    metadata_query = """
                    MATCH (n:Metadata)
                    RETURN
                        sum(CASE WHEN n:EntityTypes THEN 1 ELSE 0 END) AS entity_types_count,
                        sum(CASE WHEN n:RelationshipTypes THEN 1 ELSE 0 END) AS rel_types_count,
                        sum(CASE WHEN n:PropertySchemas THEN 1 ELSE 0 END) AS prop_schemas_count
                    """
                    result = session.run(metadata_query)
                    record = result.single()
                    
                    if not record:
                        return CheckResult(
                            Status.WARNING, 
                            "Не удалось получить информацию о метаданных в Neo4j"
                        )
                    
                    entity_types_count = record["entity_types_count"]
                    rel_types_count = record["rel_types_count"]
                    prop_schemas_count = record["prop_schemas_count"]
                    
                    # Проверяем наличие конкретных метаданных
                    if entity_types_count == 0 or rel_types_count == 0:
                        return CheckResult(
                            Status.WARNING, 
                            "Отсутствуют необходимые метаданные в Neo4j",
                            {
                                "entity_types_count": entity_types_count,
                                "relationship_types_count": rel_types_count,
                                "property_schemas_count": prop_schemas_count
                            }
                        )
                    
                    # Получаем список типов сущностей
                    entity_types_query = """
                    MATCH (n:Metadata:EntityTypes)-[:HAS_ENTITY_TYPE]->(et:EntityTypeDefinition)
                    RETURN et.name AS name
                    LIMIT 10
                    """
                    et_result = session.run(entity_types_query)
                    entity_types = [record["name"] for record in et_result]
                    
                    # Получаем список типов отношений
                    rel_types_query = """
                    MATCH (n:Metadata:RelationshipTypes)-[:HAS_RELATIONSHIP_TYPE]->(rt:RelationshipTypeDefinition)
                    RETURN rt.name AS name
                    LIMIT 10
                    """
                    rt_result = session.run(rel_types_query)
                    rel_types = [record["name"] for record in rt_result]
                    
                    # Проверяем, что определены основные типы
                    key_entity_types = ["SERVER", "APPLICATION", "PERSON", "ITService"]
                    key_rel_types = ["RUNS_ON", "DEPENDS_ON", "LOCATED_IN", "OWNED_BY"]
                    
                    missing_entity_types = [t for t in key_entity_types if t not in entity_types]
                    missing_rel_types = [t for t in key_rel_types if t not in rel_types]
                    
                    if missing_entity_types or missing_rel_types:
                        return CheckResult(
                            Status.WARNING, 
                            "Отсутствуют некоторые ключевые типы в метаданных",
                            {
                                "entity_types": entity_types,
                                "relationship_types": rel_types,
                                "missing_entity_types": missing_entity_types,
                                "missing_relationship_types": missing_rel_types
                            }
                        )
                    
                    return CheckResult(
                        Status.OK, 
                        "Метаданные в Neo4j в порядке",
                        {
                            "entity_types_count": entity_types_count,
                            "relationship_types_count": rel_types_count,
                            "property_schemas_count": prop_schemas_count,
                            "entity_types_sample": entity_types[:5],
                            "relationship_types_sample": rel_types[:5]
                        }
                    )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке метаданных в Neo4j: {str(e)}")

# ====================================================
# МОДУЛЬ 4: Диагностика API-сервиса
# ====================================================

class ApiChecker:
    """Проверка доступности и работоспособности API-сервиса"""
    
    def __init__(self, config: DiagnosticConfig):
        self.config = config
    
    def check_api_connectivity(self) -> CheckResult:
        """Проверка доступности API-сервиса"""
        try:
            # Проверяем доступность порта API
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            result = sock.connect_ex((self.config.api_host, self.config.api_port))
            sock.close()
            
            if result != 0:
                return CheckResult(
                    Status.ERROR, 
                    f"Порт API {self.config.api_port} недоступен на хосте {self.config.api_host}"
                )
            
            # Если порт доступен, пытаемся получить информацию о версии API
            try:
                response = requests.get(
                    f"{self.config.api_base_url}/api/v1/version",
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    version_info = response.json()
                    return CheckResult(
                        Status.OK, 
                        f"API-сервис доступен: {version_info.get('name', 'Unknown')} {version_info.get('version', 'Unknown')}",
                        version_info
                    )
                else:
                    return CheckResult(
                        Status.WARNING, 
                        f"API-сервис отвечает с ошибкой: {response.status_code}",
                        {"status_code": response.status_code, "response": response.text}
                    )
            except requests.exceptions.RequestException as req_error:
                return CheckResult(
                    Status.ERROR, 
                    f"Ошибка при запросе к API: {str(req_error)}"
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке доступности API: {str(e)}")
    
    def check_api_health(self) -> CheckResult:
        """Проверка здоровья API-сервиса"""
        try:
            response = requests.get(
                f"{self.config.api_base_url}/api/v1/health",
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                health_info = response.json()
                overall_status = health_info.get("status")
                
                if overall_status == "healthy":
                    return CheckResult(
                        Status.OK, 
                        "API-сервис сообщает о хорошем состоянии",
                        health_info
                    )
                else:
                    return CheckResult(
                        Status.WARNING, 
                        f"API-сервис сообщает о проблемах: {overall_status}",
                        health_info
                    )
            else:
                return CheckResult(
                    Status.ERROR, 
                    f"Ошибка при запросе health check: {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке здоровья API: {str(e)}")
    
    def check_api_detailed_health(self) -> CheckResult:
        """Проверка детального здоровья API-сервиса (требует admin-доступ)"""
        try:
            response = requests.get(
                f"{self.config.api_base_url}/api/v1/health/detailed",
                headers={"X-API-Key": self.config.api_key},
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                health_info = response.json()
                # Проверяем подключение к Neo4j через API
                neo4j_status = health_info.get("components", {}).get("neo4j", {}).get("status")
                
                if neo4j_status == "up":
                    return CheckResult(
                        Status.OK, 
                        "API-сервис подключен к Neo4j",
                        health_info
                    )
                else:
                    return CheckResult(
                        Status.WARNING, 
                        f"API-сервис сообщает о проблемах с Neo4j: {neo4j_status}",
                        health_info
                    )
            elif response.status_code == 403:
                return CheckResult(
                    Status.WARNING, 
                    "Недостаточно прав для получения детальной информации о здоровье API (требуется admin-доступ)",
                    {"status_code": response.status_code, "response": response.text}
                )
            else:
                return CheckResult(
                    Status.ERROR, 
                    f"Ошибка при запросе детального health check: {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке детального здоровья API: {str(e)}")
    
    def check_api_auth(self) -> CheckResult:
        """Проверка аутентификации в API"""
        try:
            # Проверяем доступ с правильным API-ключом
            valid_response = requests.get(
                f"{self.config.api_base_url}/api/v1/entities/types",
                headers={"X-API-Key": self.config.api_key},
                timeout=self.config.timeout
            )
            
            # Проверяем доступ с неправильным API-ключом
            invalid_response = requests.get(
                f"{self.config.api_base_url}/api/v1/entities/types",
                headers={"X-API-Key": "invalid-api-key"},
                timeout=self.config.timeout
            )
            
            # Проверяем доступ без API-ключа
            no_key_response = requests.get(
                f"{self.config.api_base_url}/api/v1/entities/types",
                timeout=self.config.timeout
            )
            
            # Анализируем результаты
            if valid_response.status_code == 200 and invalid_response.status_code == 403 and no_key_response.status_code == 403:
                return CheckResult(
                    Status.OK, 
                    "Аутентификация API работает корректно",
                    {
                        "valid_key_status": valid_response.status_code,
                        "invalid_key_status": invalid_response.status_code,
                        "no_key_status": no_key_response.status_code
                    }
                )
            else:
                issues = []
                if valid_response.status_code != 200:
                    issues.append(f"Ключ не принят ({valid_response.status_code})")
                if invalid_response.status_code != 403:
                    issues.append(f"Неверный ключ принят ({invalid_response.status_code})")
                if no_key_response.status_code != 403:
                    issues.append(f"Запрос без ключа принят ({no_key_response.status_code})")
                
                return CheckResult(
                    Status.WARNING, 
                    f"Проблемы с аутентификацией API: {', '.join(issues)}",
                    {
                        "valid_key_status": valid_response.status_code,
                        "invalid_key_status": invalid_response.status_code,
                        "no_key_status": no_key_response.status_code
                    }
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при проверке аутентификации API: {str(e)}")

# ====================================================
# МОДУЛЬ 5: Тестирование функциональности
# ====================================================

class FunctionalityTester:
    """Тестирование функциональности API"""
    
    def __init__(self, config: DiagnosticConfig):
        self.config = config
    
    def test_get_entity_types(self) -> CheckResult:
        """Тестирование получения типов сущностей"""
        try:
            response = requests.get(
                f"{self.config.api_base_url}/api/v1/entities/types",
                headers={"X-API-Key": self.config.api_key},
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                types_info = response.json()
                types_count = types_info.get("total", 0)
                
                if types_count > 0:
                    return CheckResult(
                        Status.OK, 
                        f"Получены типы сущностей ({types_count})",
                        types_info
                    )
                else:
                    return CheckResult(
                        Status.WARNING, 
                        "Получен пустой список типов сущностей",
                        types_info
                    )
            else:
                return CheckResult(
                    Status.ERROR, 
                    f"Ошибка при получении типов сущностей: {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при тестировании получения типов сущностей: {str(e)}")
    
    def test_create_entity(self) -> CheckResult:
        """Тестирование создания сущности"""
        try:
            # Создаем тестовый сервер
            test_server = {
                "name": f"TestServer-{uuid.uuid4().hex[:8]}",
                "description": "Тестовый сервер, созданный скриптом диагностики",
                "status": "Active",
                "type": "SERVER",
                "manufacturer": "Test Manufacturer",
                "model": "Test Model",
                "properties": {
                    "created_by": "diagnostic_script",
                    "creation_date": datetime.datetime.now().isoformat()
                }
            }
            
            create_response = requests.post(
                f"{self.config.api_base_url}/api/v1/entities",
                headers={
                    "X-API-Key": self.config.api_key,
                    "Content-Type": "application/json"
                },
                json=test_server,
                timeout=self.config.timeout
            )
            
            if create_response.status_code == 201:
                entity_info = create_response.json()
                entity_id = entity_info.get("id")
                
                # Проверяем, что сущность создана успешно
                get_response = requests.get(
                    f"{self.config.api_base_url}/api/v1/entities/{entity_id}",
                    headers={"X-API-Key": self.config.api_key},
                    timeout=self.config.timeout
                )
                
                if get_response.status_code == 200:
                    # Удаляем тестовую сущность
                    delete_response = requests.delete(
                        f"{self.config.api_base_url}/api/v1/entities/{entity_id}",
                        headers={"X-API-Key": self.config.api_key},
                        timeout=self.config.timeout
                    )
                    
                    deletion_successful = delete_response.status_code == 200
                    
                    return CheckResult(
                        Status.OK, 
                        f"Успешно создана и проверена сущность с ID {entity_id}",
                        {
                            "entity": entity_info,
                            "deletion_successful": deletion_successful
                        }
                    )
                else:
                    return CheckResult(
                        Status.WARNING, 
                        f"Сущность создана, но не найдена при проверке: {get_response.status_code}",
                        {
                            "entity": entity_info,
                            "get_status_code": get_response.status_code,
                            "get_response": get_response.text
                        }
                    )
            else:
                return CheckResult(
                    Status.ERROR, 
                    f"Ошибка при создании сущности: {create_response.status_code}",
                    {"status_code": create_response.status_code, "response": create_response.text}
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при тестировании создания сущности: {str(e)}")
    
    def test_create_relationship(self) -> CheckResult:
        """Тестирование создания отношения между сущностями"""
        try:
            # Создаем две тестовые сущности
            server = {
                "name": f"TestServer-{uuid.uuid4().hex[:6]}",
                "description": "Тестовый сервер для проверки отношений",
                "status": "Active",
                "type": "SERVER"
            }
            
            application = {
                "name": f"TestApp-{uuid.uuid4().hex[:6]}",
                "description": "Тестовое приложение для проверки отношений",
                "status": "Active",
                "type": "APPLICATION",
                "version": "1.0.0"
            }
            
            # Создаем сервер
            server_response = requests.post(
                f"{self.config.api_base_url}/api/v1/entities",
                headers={
                    "X-API-Key": self.config.api_key,
                    "Content-Type": "application/json"
                },
                json=server,
                timeout=self.config.timeout
            )
            
            if server_response.status_code != 201:
                return CheckResult(
                    Status.ERROR, 
                    f"Не удалось создать тестовый сервер: {server_response.status_code}",
                    {"status_code": server_response.status_code, "response": server_response.text}
                )
            
            server_id = server_response.json().get("id")
            
            # Создаем приложение
            app_response = requests.post(
                f"{self.config.api_base_url}/api/v1/entities",
                headers={
                    "X-API-Key": self.config.api_key,
                    "Content-Type": "application/json"
                },
                json=application,
                timeout=self.config.timeout
            )
            
            if app_response.status_code != 201:
                # Удаляем созданный сервер
                requests.delete(
                    f"{self.config.api_base_url}/api/v1/entities/{server_id}",
                    headers={"X-API-Key": self.config.api_key},
                    timeout=self.config.timeout
                )
                
                return CheckResult(
                    Status.ERROR, 
                    f"Не удалось создать тестовое приложение: {app_response.status_code}",
                    {"status_code": app_response.status_code, "response": app_response.text}
                )
            
            app_id = app_response.json().get("id")
            
            # Создаем отношение между сервером и приложением
            relationship = {
                "source_id": app_id,
                "target_id": server_id,
                "type": "RUNS_ON",
                "description": "Тестовое отношение для диагностики",
                "properties": {
                    "created_by": "diagnostic_script",
                    "creation_date": datetime.datetime.now().isoformat()
                }
            }
            
            rel_response = requests.post(
                f"{self.config.api_base_url}/api/v1/relations",
                headers={
                    "X-API-Key": self.config.api_key,
                    "Content-Type": "application/json"
                },
                json=relationship,
                timeout=self.config.timeout
            )
            
            # Подчищаем - удаляем созданные сущности независимо от результата
            server_deleted = False
            app_deleted = False
            
            try:
                server_delete = requests.delete(
                    f"{self.config.api_base_url}/api/v1/entities/{server_id}",
                    headers={"X-API-Key": self.config.api_key},
                    timeout=self.config.timeout
                )
                server_deleted = server_delete.status_code == 200
            except:
                pass
            
            try:
                app_delete = requests.delete(
                    f"{self.config.api_base_url}/api/v1/entities/{app_id}",
                    headers={"X-API-Key": self.config.api_key},
                    timeout=self.config.timeout
                )
                app_deleted = app_delete.status_code == 200
            except:
                pass
            
            # Анализируем результат создания отношения
            if rel_response.status_code == 201:
                relationship_info = rel_response.json()
                relationship_id = relationship_info.get("id")
                
                return CheckResult(
                    Status.OK, 
                    f"Успешно создано отношение между сущностями (ID: {relationship_id})",
                    {
                        "relationship": relationship_info,
                        "server_id": server_id,
                        "app_id": app_id,
                        "cleanup_successful": server_deleted and app_deleted
                    }
                )
            else:
                return CheckResult(
                    Status.ERROR, 
                    f"Ошибка при создании отношения: {rel_response.status_code}",
                    {
                        "status_code": rel_response.status_code, 
                        "response": rel_response.text,
                        "server_id": server_id,
                        "app_id": app_id,
                        "cleanup_successful": server_deleted and app_deleted
                    }
                )
        except Exception as e:
            return CheckResult(Status.ERROR, f"Ошибка при тестировании создания отношения: {str(e)}")

# ====================================================
# МОДУЛЬ 6: Диагностический отчет
# ====================================================

class DiagnosticReport:
    """Формирование диагностического отчета"""
    
    def __init__(self, config: DiagnosticConfig):
        self.config = config
        self.results = {}
        self.start_time = datetime.datetime.now()
        self.end_time = None
    
    def add_result(self, category: str, check_name: str, result: CheckResult):
        """Добавить результат проверки в отчет"""
        if category not in self.results:
            self.results[category] = {}
        
        self.results[category][check_name] = result
    
    def generate_summary(self) -> Dict[str, Any]:
        """Сгенерировать сводную информацию"""
        self.end_time = datetime.datetime.now()
        
        # Подсчитываем статистику по статусам
        status_counts = {status.name: 0 for status in Status}
        
        for category in self.results:
            for check_name, result in self.results[category].items():
                status_counts[result.status.name] += 1
        
        # Определяем общий статус системы
        overall_status = Status.OK
        if status_counts[Status.ERROR.name] > 0:
            overall_status = Status.ERROR
        elif status_counts[Status.WARNING.name] > 0:
            overall_status = Status.WARNING
        
        return {
            "overall_status": overall_status.name,
            "status_counts": status_counts,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds()
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Сгенерировать полный отчет"""
        summary = self.generate_summary()
        
        # Формируем рекомендации на основе результатов
        recommendations = self._generate_recommendations()
        
        # Формируем полный отчет
        report = {
            "summary": summary,
            "config": {
                "api_host": self.config.api_host,
                "api_port": self.config.api_port,
                "neo4j_host": self.config.neo4j_host,
                "neo4j_port": self.config.neo4j_port,
                "using_docker": self.config.using_docker
            },
            "results": {},
            "recommendations": recommendations
        }
        
        # Преобразуем результаты в формат для отчета
        for category, checks in self.results.items():
            report["results"][category] = {}
            for check_name, result in checks.items():
                report["results"][category][check_name] = {
                    "status": result.status.name,
                    "message": result.message
                }
                if self.config.verbose and result.details:
                    report["results"][category][check_name]["details"] = result.details
        
        return report
    
    def print_report(self):
        """Вывести отчет в консоль"""
        report = self.generate_report()
        summary = report["summary"]
        
        print("\n" + "="*80)
        print(f"DEMENTOR CMDB ДИАГНОСТИЧЕСКИЙ ОТЧЕТ")
        print("="*80)
        
        print(f"\nДата и время: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Длительность: {summary['duration_seconds']:.2f} секунд\n")
        
        print(f"Общий статус системы: {summary['overall_status']}")
        print(f"Итого проверок: {sum(summary['status_counts'].values())}")
        print(f"  OK: {summary['status_counts']['OK']}")
        print(f"  WARNING: {summary['status_counts']['WARNING']}")
        print(f"  ERROR: {summary['status_counts']['ERROR']}")
        print(f"  SKIPPED: {summary['status_counts']['SKIPPED']}")
        
        print("\nРезультаты проверок:")
        for category, checks in report["results"].items():
            print(f"\n{category}:")
            for check_name, result in checks.items():
                status_marker = {
                    "OK": "✓",
                    "WARNING": "⚠",
                    "ERROR": "✗",
                    "SKIPPED": "-"
                }.get(result["status"], "?")
                
                print(f"  {status_marker} {check_name}: {result['message']}")
        
        print("\nРекомендации:")
        if report["recommendations"]:
            for rec in report["recommendations"]:
                print(f"  - {rec}")
        else:
            print("  - Рекомендаций нет. Система работает корректно.")
        
        print("\n" + "="*80 + "\n")
    
    def save_report(self, filename: str = "cmdb_diagnostics_report.json"):
        """Сохранить отчет в файл"""
        report = self.generate_report()
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Отчет сохранен в файл: {filename}")
    
    def _generate_recommendations(self) -> List[str]:
        """Сгенерировать рекомендации на основе результатов проверок"""
        recommendations = []
        
        # Проверяем подключение к Neo4j
        if "Neo4j" in self.results:
            if "connectivity" in self.results["Neo4j"] and self.results["Neo4j"]["connectivity"].status != Status.OK:
                recommendations.append(
                    f"Проверьте доступность Neo4j по адресу {self.config.neo4j_host}:{self.config.neo4j_port}"
                )
            
            if "authentication" in self.results["Neo4j"] and self.results["Neo4j"]["authentication"].status != Status.OK:
                recommendations.append(
                    "Проверьте учетные данные для подключения к Neo4j (логин/пароль)"
                )
            
            if "metadata" in self.results["Neo4j"] and self.results["Neo4j"]["metadata"].status != Status.OK:
                recommendations.append(
                    "Инициализируйте метаданные в Neo4j с помощью скрипта base-init.sh"
                )
        
        # Проверяем API-сервис
        if "API" in self.results:
            if "connectivity" in self.results["API"] and self.results["API"]["connectivity"].status != Status.OK:
                recommendations.append(
                    f"Проверьте запуск API-сервиса по адресу {self.config.api_host}:{self.config.api_port}"
                )
            
            if "health" in self.results["API"] and self.results["API"]["health"].status != Status.OK:
                recommendations.append(
                    "API-сервис сообщает о проблемах со здоровьем. Проверьте логи сервиса."
                )
            
            if "auth" in self.results["API"] and self.results["API"]["auth"].status != Status.OK:
                recommendations.append(
                    "Проверьте настройки API-ключей в конфигурации"
                )
        
        # Проверяем функциональность
        if "Functionality" in self.results:
            if "create_entity" in self.results["Functionality"] and self.results["Functionality"]["create_entity"].status != Status.OK:
                recommendations.append(
                    "Невозможно создать конфигурационную единицу. Проверьте соединение между API и Neo4j."
                )
            
            if "create_relationship" in self.results["Functionality"] and self.results["Functionality"]["create_relationship"].status != Status.OK:
                recommendations.append(
                    "Невозможно создать отношение между КЕ. Проверьте метаданные типов отношений."
                )
        
        # Проверяем окружение
        if "Environment" in self.results:
            if "python_version" in self.results["Environment"] and self.results["Environment"]["python_version"].status != Status.OK:
                recommendations.append(
                    "Рекомендуется использовать Python 3.10 или выше"
                )
            
            if "dependencies" in self.results["Environment"] and self.results["Environment"]["dependencies"].status != Status.OK:
                recommendations.append(
                    "Установите недостающие зависимости: pip install -r requirements.txt"
                )
            
            if "docker" in self.results["Environment"] and self.results["Environment"]["docker"].status != Status.OK and self.config.using_docker:
                recommendations.append(
                    "Проверьте установку Docker и Docker Compose для запуска в контейнерах"
                )
        
        return recommendations

# ====================================================
# МОДУЛЬ 7: Основная логика
# ====================================================

def main():
    """Основная функция диагностики"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Dementor CMDB API - Диагностический скрипт")
    parser.add_argument("--host", help="Хост API-сервиса (по умолчанию: localhost)")
    parser.add_argument("--port", type=int, help="Порт API-сервиса (по умолчанию: 8000)")
    parser.add_argument("--api-key", help="API-ключ для авторизации")
    parser.add_argument("--neo4j-host", help="Хост Neo4j (по умолчанию: localhost)")
    parser.add_argument("--neo4j-port", type=int, help="Порт Neo4j (по умолчанию: 7687)")
    parser.add_argument("--neo4j-user", help="Имя пользователя Neo4j (по умолчанию: neo4j)")
    parser.add_argument("--neo4j-password", help="Пароль Neo4j")
    parser.add_argument("--timeout", type=int, help="Таймаут для запросов в секундах (по умолчанию: 10)")
    parser.add_argument("--config", help="Путь к файлу конфигурации (по умолчанию: config.yml)")
    parser.add_argument("--docker", action="store_true", help="Использовать Docker-окружение")
    parser.add_argument("--docker-compose-file", help="Путь к файлу docker-compose.yml")
    parser.add_argument("--verbose", action="store_true", help="Подробный вывод")
    parser.add_argument("--output", help="Путь для сохранения отчета")
    
    args = parser.parse_args()
    
    # Инициализация конфигурации
    config = DiagnosticConfig()
    
    # Загружаем конфигурацию из файла, если он указан
    if args.config:
        config.load_from_config(args.config)
    else:
        config.load_from_config("config.yml")
    
    # Применяем аргументы командной строки (они имеют приоритет)
    config.load_from_args(args)
    
    # Инициализация отчета
    report = DiagnosticReport(config)
    
    # Отображаем стартовое сообщение
    print("\nDementor CMDB API - Диагностический скрипт")
    print("Выполняется диагностика системы...")
    print(f"API: {config.api_base_url}, Neo4j: {config.neo4j_uri}\n")
    
    # Проверка окружения
    env_checker = EnvironmentChecker(config)
    
    result = env_checker.check_python_version()
    report.add_result("Environment", "python_version", result)
    print(f"Проверка версии Python: {result.status.name} - {result.message}")
    
    result = env_checker.check_dependencies()
    report.add_result("Environment", "dependencies", result)
    print(f"Проверка зависимостей: {result.status.name} - {result.message}")
    
    result = env_checker.check_docker()
    report.add_result("Environment", "docker", result)
    if result.status != Status.SKIPPED:
        print(f"Проверка Docker: {result.status.name} - {result.message}")
    
    result = env_checker.check_file_permissions()
    report.add_result("Environment", "file_permissions", result)
    print(f"Проверка прав на файлы: {result.status.name} - {result.message}")
    
    # Проверка Neo4j
    neo4j_checker = Neo4jChecker(config)
    
    result = neo4j_checker.check_neo4j_connectivity()
    report.add_result("Neo4j", "connectivity", result)
    print(f"Проверка соединения с Neo4j: {result.status.name} - {result.message}")
    
    # Если соединение с Neo4j успешно, проверяем авторизацию и метаданные
    if result.status == Status.OK:
        result = neo4j_checker.check_neo4j_authentication()
        report.add_result("Neo4j", "authentication", result)
        print(f"Проверка аутентификации в Neo4j: {result.status.name} - {result.message}")
        
        result = neo4j_checker.check_neo4j_metadata()
        report.add_result("Neo4j", "metadata", result)
        print(f"Проверка метаданных в Neo4j: {result.status.name} - {result.message}")
    
    # Проверка API-сервиса
    api_checker = ApiChecker(config)
    
    result = api_checker.check_api_connectivity()
    report.add_result("API", "connectivity", result)
    print(f"Проверка доступности API: {result.status.name} - {result.message}")
    
    # Если API доступен, проверяем его здоровье и аутентификацию
    if result.status == Status.OK:
        result = api_checker.check_api_health()
        report.add_result("API", "health", result)
        print(f"Проверка здоровья API: {result.status.name} - {result.message}")
        
        result = api_checker.check_api_detailed_health()
        report.add_result("API", "detailed_health", result)
        print(f"Проверка детального здоровья API: {result.status.name} - {result.message}")
        
        result = api_checker.check_api_auth()
        report.add_result("API", "auth", result)
        print(f"Проверка аутентификации API: {result.status.name} - {result.message}")
        
        # Тестирование функциональности
        func_tester = FunctionalityTester(config)
        
        result = func_tester.test_get_entity_types()
        report.add_result("Functionality", "get_entity_types", result)
        print(f"Тест получения типов сущностей: {result.status.name} - {result.message}")
        
        result = func_tester.test_create_entity()
        report.add_result("Functionality", "create_entity", result)
        print(f"Тест создания сущности: {result.status.name} - {result.message}")
        
        result = func_tester.test_create_relationship()
        report.add_result("Functionality", "create_relationship", result)
        print(f"Тест создания отношения: {result.status.name} - {result.message}")
    
    # Формируем и выводим отчет
    report.print_report()
    
    # Сохраняем отчет в файл, если указан путь
    if args.output:
        report.save_report(args.output)
    else:
        # По умолчанию сохраняем отчет с временной меткой
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report.save_report(f"cmdb_diagnostics_report_{timestamp}.json")

if __name__ == "__main__":
    main()
