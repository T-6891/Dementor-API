# Dementor CMDB API

API-сервис для управления конфигурационной базой данных (CMDB) на базе Neo4j.

## Описание

Dementor CMDB API предоставляет REST API для работы с базой данных конфигурационных единиц (КЕ), хранящейся в графовой СУБД Neo4j. Сервис обеспечивает полный цикл управления конфигурационными единицами и их отношениями, включая создание, чтение, обновление и удаление (CRUD-операции).

## Ключевые возможности

- Подключение к Neo4j Community Edition
- Авторизация по API-ключам
- Проверка здоровья всех компонентов (health check)
- Управление конфигурационными единицами (КЕ)
- Управление отношениями между КЕ
- Поиск и фильтрация КЕ и отношений
- Масштабируемая и модульная архитектура

## Технологии

- Python 3.10+
- FastAPI
- Neo4j (Community Edition)
- Docker
- Pydantic
- Uvicorn

## Предварительные требования

- Python 3.10+
- Neo4j (версия 4.4+)
- Docker и Docker Compose (опционально)

## Установка и запуск

### Локальная установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/dementor-cmdb.git
   cd dementor-cmdb
   ```

2. Создайте и активируйте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Настройте конфигурацию в файле `config.yml` или через переменные окружения.

5. Запустите приложение:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Запуск с Docker Compose

1. Настройте переменные окружения в файле `docker-compose.yml` при необходимости.

2. Запустите контейнеры:
   ```bash
   docker-compose up -d
   ```

3. Для инициализации схемы Neo4j выполните скрипт:
   ```bash
   docker-compose exec neo4j bash /var/lib/neo4j/import/base-init.sh
   ```

## Конфигурация

Конфигурация приложения осуществляется через:

1. Файл `config.yml`
2. Переменные окружения:
   - `CMDB_NEO4J_HOST` - хост Neo4j (по умолчанию: localhost)
   - `CMDB_NEO4J_PORT` - порт Neo4j (по умолчанию: 7687)
   - `CMDB_NEO4J_USER` - пользователь Neo4j (по умолчанию: neo4j)
   - `CMDB_NEO4J_PASSWORD` - пароль Neo4j
   - `CMDB_NEO4J_DATABASE` - база данных Neo4j (по умолчанию: neo4j)
   - `CMDB_API_KEYS` - API-ключи в формате "client_id:key:permissions;client_id2:key2:permissions2"

## API-ключи и авторизация

API использует механизм авторизации по API-ключам. Ключи настраиваются в конфигурационном файле или через переменные окружения.

Пример формата для переменной `CMDB_API_KEYS`:
```
admin:admin-api-key:read,write,admin;monitor:monitor-api-key:read
```

Для авторизации API-запросов используйте заголовок `X-API-Key`:
```
X-API-Key: your-api-key
```

## Основные эндпоинты API

### Документация API
- `/api/docs` - Swagger UI с документацией API
- `/api/redoc` - ReDoc с документацией API

### Проверка здоровья
- `GET /api/v1/health` - Проверка состояния системы
- `GET /api/v1/health/detailed` - Детальная проверка состояния (требуется admin-доступ)
- `GET /api/v1/version` - Информация о версии API

### Сущности
- `GET /api/v1/entities` - Получить список сущностей
- `GET /api/v1/entities/{entity_id}` - Получить сущность по ID
- `POST /api/v1/entities` - Создать новую сущность
- `PUT /api/v1/entities/{entity_id}` - Обновить сущность
- `DELETE /api/v1/entities/{entity_id}` - Удалить сущность
- `GET /api/v1/entities/types` - Получить список типов сущностей
- `GET /api/v1/entities/{entity_id}/related` - Получить связанные сущности
- `GET /api/v1/entities/search` - Поиск сущностей

### Отношения
- `GET /api/v1/relations` - Получить список отношений
- `GET /api/v1/relations/{relation_id}` - Получить отношение по ID
- `POST /api/v1/relations` - Создать новое отношение
- `PUT /api/v1/relations/{relation_id}` - Обновить отношение
- `DELETE /api/v1/relations/{relation_id}` - Удалить отношение
- `GET /api/v1/relations/types` - Получить список типов отношений
- `POST /api/v1/relations/bulk` - Массовое создание отношений
- `POST /api/v1/relations/bulk/delete` - Массовое удаление отношений

## Примеры использования

### Создание сервера

```bash
curl -X POST "http://localhost:8000/api/v1/entities/servers" \
  -H "X-API-Key: admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "app-server-01",
    "description": "Application server in DataCenter 1",
    "status": "Active",
    "manufacturer": "Dell",
    "model": "PowerEdge R740",
    "serial_number": "SN12345678"
  }'
```

### Создание отношения между сервером и приложением

```bash
curl -X POST "http://localhost:8000/api/v1/relations" \
  -H "X-API-Key: admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "SRV123456",
    "target_id": "APP123456",
    "type": "HOSTS",
    "description": "Server hosts application",
    "properties": {
      "deployment_date": "2023-01-01"
    }
  }'
```

## Мониторинг

API предоставляет эндпоинт `/api/v1/health` для мониторинга состояния сервиса и его компонентов. Данный эндпоинт доступен без авторизации и может использоваться системами мониторинга.

## Инициализация базы данных

Для инициализации схемы Neo4j используется скрипт `base-init.sh`, который создает:
- Ограничения уникальности для ключевых сущностей
- Индексы для ускорения запросов
- Метаданные для типов сущностей
- Метаданные для типов отношений
- Схемы свойств для валидации данных

## Разработка

### Структура проекта

```
dementor-cmdb/
│
├── app/                     # Основной код приложения
│   ├── api/                 # API endpoints
│   ├── core/                # Ядро приложения
│   ├── db/                  # Работа с базой данных
│   ├── models/              # Модели данных
│   ├── schemas/             # Pydantic схемы
│   ├── services/            # Сервисы бизнес-логики
│   └── static/              # Статические файлы
│
├── tests/                   # Тесты
├── config.yml              # Конфигурационный файл
├── Dockerfile              # Для создания контейнера
└── docker-compose.yml      # Для локальной разработки
```

### Запуск тестов

```bash
pytest
```

## Лицензия

[MIT License](LICENSE)

## Авторы

[Your Name] - [your-email@example.com]