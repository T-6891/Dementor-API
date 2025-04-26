#!/bin/bash
# ==============================================================================
# CMDB Initialization Script for Neo4j v3.0 (Optimized)
# ==============================================================================
# Description:
#   Этот скрипт инициализирует схему для Configuration Management Database (CMDB)
#   в графовой СУБД Neo4j. Он создает:
#     - Ограничения уникальности (Constraints) для ключевых сущностей.
#     - Индексы (Indexes) для ускорения запросов.
#     - Метаданные для Типов Сущностей (Entity Types).
#     - Метаданные для Типов Отношений (Relationship Types).
#     - Схемы Свойств (Property Schemas) для валидации данных основных сущностей.
#
# Usage:
#   1. Настройте параметры подключения ниже (NEO4J_*) или используйте
#      переменные окружения.
#   2. Убедитесь, что 'cypher-shell' доступен в PATH или укажите путь.
#   3. Сделайте скрипт исполняемым: chmod +x cmdb_init_optimized.sh
#   4. Запустите: ./cmdb_init_optimized.sh [флаги]
#
# Optional Flags:
#   --skip-constraints    Пропустить создание ограничений
#   --skip-indexes        Пропустить создание индексов
#   --skip-entity-meta    Пропустить создание метаданных сущностей
#   --skip-relation-meta  Пропустить создание метаданных отношений
#   --skip-prop-schemas   Пропустить создание схем свойств
#   --skip-verify         Пропустить финальную проверку
#   --help                Показать это сообщение
#
# Prerequisites:
#   - Запущенный экземпляр Neo4j.
#   - Установленный 'cypher-shell'.
#   - Права на выполнение запросов к Neo4j у указанного пользователя.
# ==============================================================================

# --- Configuration ---
# Рекомендуется использовать переменные окружения или внешний config-файл
# source ./cmdb_config.env
NEO4J_HOST="${NEO4J_HOST:-localhost}"
NEO4J_PORT="${NEO4J_PORT:-7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-656D614e+}" # !!! СМЕНИТЕ ПАРОЛЬ !!!
CYPHER_SHELL_CMD="cypher-shell" # Можно указать полный путь, если не в PATH

# --- Flags ---
SKIP_CONSTRAINTS=false
SKIP_INDEXES=false
SKIP_ENTITY_META=false
SKIP_RELATION_META=false
SKIP_PROP_SCHEMAS=false
SKIP_VERIFY=false

# --- Command Line Argument Parsing ---
show_help() {
    grep '^# Optional Flags:' "$0" | cut -c3-
    exit 0
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --skip-constraints) SKIP_CONSTRAINTS=true ;;
        --skip-indexes) SKIP_INDEXES=true ;;
        --skip-entity-meta) SKIP_ENTITY_META=true ;;
        --skip-relation-meta) SKIP_RELATION_META=true ;;
        --skip-prop-schemas) SKIP_PROP_SCHEMAS=true ;;
        --skip-verify) SKIP_VERIFY=true ;;
        --help) show_help ;;
        *) echo "Неизвестный параметр: $1"; show_help; exit 1 ;;
    esac
    shift
done

# --- Helper Functions ---
log_message() {
    echo ">>> $1"
}

error_exit() {
    echo "!!! ОШИБКА: $1" >&2
    exit 1
}

# Function to execute Cypher queries
execute_cypher() {
    local query="$1"
    local query_short="${query//[$'\t\r\n']/ }" # Убираем переносы для краткого лога
    echo "Выполнение Cypher: ${query_short:0:100}..."

    "$CYPHER_SHELL_CMD" -a "$NEO4J_HOST:$NEO4J_PORT" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "$query"

    if [ $? -ne 0 ]; then
        error_exit "Ошибка при выполнении запроса Cypher. Запрос: ${query_short:0:200}..."
    fi
}

# --- Dependency Check ---
log_message "Проверка наличия '$CYPHER_SHELL_CMD'..."
if ! command -v "$CYPHER_SHELL_CMD" &> /dev/null; then
    # Попробуем найти в стандартном месте установки Neo4j (пример)
    if [ -x "/usr/share/neo4j/bin/$CYPHER_SHELL_CMD" ]; then
        CYPHER_SHELL_CMD="/usr/share/neo4j/bin/$CYPHER_SHELL_CMD"
        log_message "Найдено в /usr/share/neo4j/bin/"
    elif [ -x "/var/lib/neo4j/bin/$CYPHER_SHELL_CMD" ]; then
        CYPHER_SHELL_CMD="/var/lib/neo4j/bin/$CYPHER_SHELL_CMD"
         log_message "Найдено в /var/lib/neo4j/bin/"
    else
        error_exit "'$CYPHER_SHELL_CMD' не найден в PATH или стандартных директориях. Установите 'neo4j' или 'neo4j-client' или укажите путь к '$CYPHER_SHELL_CMD' в скрипте."
    fi
fi
log_message "'$CYPHER_SHELL_CMD' найден."

# --- Schema Initialization Functions ---

# 1. Create Constraints
create_constraints() {
    log_message "--- [1/6] Создание ограничений уникальности (Constraints) ---"

    # Используем более уникальные метки, где были конфликты в оригинале
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE;"
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Department) REQUIRE d.id IS UNIQUE;"
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE;"
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;"
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (ro:Role) REQUIRE ro.id IS UNIQUE;" # Role -> ro

    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE;"
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Building) REQUIRE b.id IS UNIQUE;"
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (rm:Room) REQUIRE rm.id IS UNIQUE;" # Room -> rm
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (rk:Rack) REQUIRE rk.id IS UNIQUE;" # Rack -> rk
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (dc:DataCenter) REQUIRE dc.id IS UNIQUE;" # DataCenter -> dc

    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (h:HardwareAsset) REQUIRE h.id IS UNIQUE;"
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (srv:Server) REQUIRE srv.id IS UNIQUE;" # Server -> srv
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (vs:VirtualServer) REQUIRE vs.id IS UNIQUE;" # VirtualServer -> vs
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (nd:NetworkDevice) REQUIRE nd.id IS UNIQUE;" # NetworkDevice -> nd
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (sd:StorageDevice) REQUIRE sd.id IS UNIQUE;" # StorageDevice -> sd
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Endpoint) REQUIRE e.id IS UNIQUE;"

    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (sa:SoftwareAsset) REQUIRE sa.id IS UNIQUE;" # SoftwareAsset -> sa
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (os:OperatingSystem) REQUIRE os.id IS UNIQUE;" # OperatingSystem -> os
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (app:Application) REQUIRE app.id IS UNIQUE;" # Application -> app
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (db:Database) REQUIRE db.id IS UNIQUE;" # Database -> db
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (mw:Middleware) REQUIRE mw.id IS UNIQUE;" # Middleware -> mw
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (sws:ServiceSoftware) REQUIRE sws.id IS UNIQUE;" # ServiceSoftware -> sws

    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (bs:BusinessService) REQUIRE bs.id IS UNIQUE;" # BusinessService -> bs
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (its:ITService) REQUIRE its.id IS UNIQUE;" # ITService -> its
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (bp:BusinessProcess) REQUIRE bp.id IS UNIQUE;" # BusinessProcess -> bp
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (sc:ServiceComponent) REQUIRE sc.id IS UNIQUE;" # ServiceComponent -> sc
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (ctr:Contract) REQUIRE ctr.id IS UNIQUE;" # Contract -> ctr
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (sla:SLA) REQUIRE sla.id IS UNIQUE;" # SLA -> sla

    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (net:Network) REQUIRE net.id IS UNIQUE;" # Network -> net
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (sub:Subnet) REQUIRE sub.id IS UNIQUE;" # Subnet -> sub
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (vl:VLAN) REQUIRE vl.id IS UNIQUE;" # VLAN -> vl
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (ip:IPAddress) REQUIRE ip.id IS UNIQUE;" # IPAddress -> ip
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (fw:FirewallRule) REQUIRE fw.id IS UNIQUE;" # FirewallRule -> fw
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (ns:NetworkSegment) REQUIRE ns.id IS UNIQUE;" # NetworkSegment -> ns

    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (inc:Incident) REQUIRE inc.id IS UNIQUE;" # Incident -> inc
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (prb:Problem) REQUIRE prb.id IS UNIQUE;" # Problem -> prb
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (chg:Change) REQUIRE chg.id IS UNIQUE;" # Change -> chg
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (rel:Release) REQUIRE rel.id IS UNIQUE;" # Release -> rel
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (tkt:Ticket) REQUIRE tkt.id IS UNIQUE;" # Ticket -> tkt
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (mnt:Maintenance) REQUIRE mnt.id IS UNIQUE;" # Maintenance -> mnt

    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (sec:SecurityControl) REQUIRE sec.id IS UNIQUE;" # SecurityControl -> sec
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (sp:SecurityPolicy) REQUIRE sp.id IS UNIQUE;" # SecurityPolicy -> sp
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (vul:Vulnerability) REQUIRE vul.id IS UNIQUE;" # Vulnerability -> vul
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (cr:ComplianceRequirement) REQUIRE cr.id IS UNIQUE;" # ComplianceRequirement -> cr
    execute_cypher "CREATE CONSTRAINT IF NOT EXISTS FOR (ac:AccessControl) REQUIRE ac.id IS UNIQUE;" # AccessControl -> ac

    log_message "Создание ограничений завершено."
}

# 2. Create Indexes
create_indexes() {
    log_message "--- [2/6] Создание индексов (Indexes) ---"
    # Используем метки, согласованные с constraints
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (o:Organization) ON (o.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (d:Department) ON (d.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (t:Team) ON (t.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.email);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (srv:Server) ON (srv.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (vs:VirtualServer) ON (vs.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (app:Application) ON (app.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (its:ITService) ON (its.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (inc:Incident) ON (inc.created_at);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (chg:Change) ON (chg.created_at);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (dc:DataCenter) ON (dc.name);"
    execute_cypher "CREATE INDEX IF NOT EXISTS FOR (ip:IPAddress) ON (ip.address);"
    log_message "Создание индексов завершено."
}

# 3. Create Entity Type Metadata
create_entity_metadata() {
    log_message "--- [3/6] Создание метаданных: Типы сущностей (Entity Types) ---"
    # Этот длинный запрос можно вынести в отдельный .cypher файл
    local query="
    MERGE (n:Metadata:EntityTypes)
      ON CREATE SET n.created_at = datetime(), n.description = 'Типы объектов конфигурации CMDB'
    WITH n
    UNWIND [
      {name: 'Organization', description: 'Юридическое лицо или подразделение холдинга', category: 'Organization'},
      {name: 'Department', description: 'Департамент или отдел', category: 'Organization'},
      {name: 'Team', description: 'Команда или служба', category: 'Organization'},
      {name: 'Person', description: 'Сотрудник или пользователь', category: 'Organization'},
      {name: 'Role', description: 'Должность или роль пользователя', category: 'Organization'},
      {name: 'Location', description: 'Физическое местоположение', category: 'Location'},
      {name: 'Building', description: 'Здание', category: 'Location'},
      {name: 'Room', description: 'Помещение', category: 'Location'},
      {name: 'Rack', description: 'Стойка для оборудования', category: 'Location'},
      {name: 'DataCenter', description: 'Центр обработки данных', category: 'Location'},
      {name: 'HardwareAsset', description: 'Физический аппаратный актив', category: 'Hardware'},
      {name: 'Server', description: 'Физический сервер', category: 'Hardware'},
      {name: 'VirtualServer', description: 'Виртуальный сервер', category: 'Hardware'},
      {name: 'NetworkDevice', description: 'Сетевое устройство', category: 'Hardware'},
      {name: 'StorageDevice', description: 'Система хранения данных', category: 'Hardware'},
      {name: 'Endpoint', description: 'Конечное устройство пользователя', category: 'Hardware'},
      {name: 'SoftwareAsset', description: 'Программный актив', category: 'Software'},
      {name: 'OperatingSystem', description: 'Операционная система', category: 'Software'},
      {name: 'Application', description: 'Прикладное ПО', category: 'Software'},
      {name: 'Database', description: 'База данных', category: 'Software'},
      {name: 'Middleware', description: 'Промежуточное ПО', category: 'Software'},
      {name: 'ServiceSoftware', description: 'Программный сервис', category: 'Software'},
      {name: 'BusinessService', description: 'Бизнес-сервис', category: 'Service'},
      {name: 'ITService', description: 'ИТ-сервис', category: 'Service'},
      {name: 'BusinessProcess', description: 'Бизнес-процесс', category: 'Service'},
      {name: 'ServiceComponent', description: 'Компонент сервиса', category: 'Service'},
      {name: 'Contract', description: 'Контракт на обслуживание', category: 'Service'},
      {name: 'SLA', description: 'Соглашение об уровне сервиса', category: 'Service'},
      {name: 'Network', description: 'Сеть', category: 'Network'},
      {name: 'Subnet', description: 'Подсеть', category: 'Network'},
      {name: 'VLAN', description: 'Виртуальная локальная сеть', category: 'Network'},
      {name: 'IPAddress', description: 'IP-адрес', category: 'Network'},
      {name: 'FirewallRule', description: 'Правило межсетевого экрана', category: 'Network'},
      {name: 'NetworkSegment', description: 'Сегмент сети', category: 'Network'},
      {name: 'Incident', description: 'Инцидент', category: 'ChangeManagement'},
      {name: 'Problem', description: 'Проблема', category: 'ChangeManagement'},
      {name: 'Change', description: 'Запрос на изменение', category: 'ChangeManagement'},
      {name: 'Release', description: 'Релиз', category: 'ChangeManagement'},
      {name: 'Ticket', description: 'Заявка пользователя', category: 'ChangeManagement'},
      {name: 'Maintenance', description: 'Плановое обслуживание', category: 'ChangeManagement'},
      {name: 'SecurityControl', description: 'Мера безопасности', category: 'Security'},
      {name: 'SecurityPolicy', description: 'Политика безопасности', category: 'Security'},
      {name: 'Vulnerability', description: 'Уязвимость', category: 'Security'},
      {name: 'ComplianceRequirement', description: 'Требование соответствия', category: 'Security'},
      {name: 'AccessControl', description: 'Контроль доступа', category: 'Security'}
    ] AS entityType
    MERGE (et:EntityTypeDefinition {name: entityType.name})
      ON CREATE SET et.description = entityType.description, et.category = entityType.category
    MERGE (n)-[:HAS_ENTITY_TYPE]->(et);
    "
    execute_cypher "$query"
    log_message "Создание метаданных сущностей завершено."
}

# 4. Create Relationship Type Metadata
create_relationship_metadata() {
    log_message "--- [4/6] Создание метаданных: Типы отношений (Relationship Types) ---"
    local query="
    MERGE (n:Metadata:RelationshipTypes)
      ON CREATE SET n.created_at = datetime(), n.description = 'Типы отношений между объектами конфигурации CMDB'
    WITH n
    UNWIND [
      {name: 'BELONGS_TO', description: 'Принадлежит к', category: 'Organization'},
      {name: 'REPORTS_TO', description: 'Подчиняется', category: 'Organization'},
      {name: 'MANAGES', description: 'Управляет', category: 'Organization'},
      {name: 'WORKS_IN', description: 'Работает в', category: 'Organization'},
      {name: 'HAS_ROLE', description: 'Имеет роль', category: 'Organization'},
      {name: 'LOCATED_IN', description: 'Находится в', category: 'Physical'},
      {name: 'CONTAINS', description: 'Содержит', category: 'Physical'},
      {name: 'ADJACENT_TO', description: 'Смежен с', category: 'Physical'},
      {name: 'MOUNTED_IN', description: 'Установлен в', category: 'Physical'},
      {name: 'RUNS_ON', description: 'Выполняется на', category: 'Technical'},
      {name: 'CONNECTS_TO', description: 'Соединяется с', category: 'Technical'},
      {name: 'DEPENDS_ON', description: 'Зависит от', category: 'Technical'},
      {name: 'HOSTS', description: 'Размещает', category: 'Technical'},
      {name: 'PART_OF', description: 'Является частью', category: 'Technical'},
      {name: 'INSTALLED_ON', description: 'Установлен на', category: 'Technical'},
      {name: 'COMMUNICATES_WITH', description: 'Взаимодействует с', category: 'Technical'},
      {name: 'PROVIDES', description: 'Предоставляет', category: 'Service'},
      {name: 'CONSUMES', description: 'Потребляет', category: 'Service'},
      {name: 'SUPPORTS', description: 'Поддерживает', category: 'Service'},
      {name: 'IMPLEMENTS', description: 'Реализует', category: 'Service'},
      {name: 'DELIVERS', description: 'Доставляет', category: 'Service'},
      {name: 'RESPONSIBLE_FOR', description: 'Ответственен за', category: 'Responsibility'},
      {name: 'OWNS', description: 'Владеет', category: 'Responsibility'},
      {name: 'ASSIGNED_TO', description: 'Назначен', category: 'Responsibility'},
      {name: 'SUPPORTS_L1', description: 'Поддерживает (1-я линия)', category: 'Responsibility'},
      {name: 'SUPPORTS_L2', description: 'Поддерживает (2-я линия)', category: 'Responsibility'},
      {name: 'SUPPORTS_L3', description: 'Поддерживает (3-я линия)', category: 'Responsibility'},
      {name: 'ADMINISTERS', description: 'Администрирует', category: 'Responsibility'},
      {name: 'AFFECTS', description: 'Влияет на', category: 'ChangeManagement'},
      {name: 'RESOLVES', description: 'Разрешает', category: 'ChangeManagement'},
      {name: 'RELATED_TO', description: 'Связан с', category: 'ChangeManagement'},
      {name: 'CAUSED_BY', description: 'Вызван', category: 'ChangeManagement'},
      {name: 'REQUESTED_BY', description: 'Запрошен', category: 'ChangeManagement'},
      {name: 'IMPLEMENTED_BY', description: 'Реализован', category: 'ChangeManagement'},
      {name: 'PROTECTS', description: 'Защищает', category: 'Security'},
      {name: 'ENFORCES', description: 'Обеспечивает', category: 'Security'},
      {name: 'COMPLIES_WITH', description: 'Соответствует', category: 'Security'},
      {name: 'HAS_VULNERABILITY', description: 'Имеет уязвимость', category: 'Security'},
      {name: 'MITIGATES', description: 'Смягчает', category: 'Security'},
      {name: 'GRANTS_ACCESS', description: 'Предоставляет доступ', category: 'Security'},
      {name: 'PRECEDES', description: 'Предшествует', category: 'Temporal'},
      {name: 'SUCCEEDED_BY', description: 'Сменяется', category: 'Temporal'},
      {name: 'SCHEDULED_FOR', description: 'Запланирован на', category: 'Temporal'},
      {name: 'VALID_FROM', description: 'Действителен с', category: 'Temporal'},
      {name: 'VALID_TO', description: 'Действителен до', category: 'Temporal'},
      {name: 'DEFINED_IN', description: 'Определен в', category: 'Business'},
      {name: 'REFERENCED_BY', description: 'Упоминается в', category: 'Business'},
      {name: 'CONTRIBUTES_TO', description: 'Способствует', category: 'Business'},
      {name: 'REGULATED_BY', description: 'Регулируется', category: 'Business'},
      {name: 'HAS_SLA', description: 'Имеет SLA', category: 'Business'}
    ] AS relType
    MERGE (rt:RelationshipTypeDefinition {name: relType.name})
      ON CREATE SET rt.description = relType.description, rt.category = relType.category
    MERGE (n)-[:HAS_RELATIONSHIP_TYPE]->(rt);
    "
    execute_cypher "$query"
    log_message "Создание метаданных отношений завершено."
}

# 5. Create Property Schemas for key entities
create_property_schemas() {
    log_message "--- [5/6] Создание схем атрибутов (Property Schemas) ---"
    execute_cypher "MERGE (n:Metadata:PropertySchemas) ON CREATE SET n.created_at = datetime(), n.description = 'Схемы атрибутов для основных типов объектов конфигурации';"

    # Schema: Server (using label 'Server' as defined in entity metadata)
    execute_cypher "
    MATCH (n:Metadata:PropertySchemas)
    MERGE (ps:PropertySchema { entityType: 'Server' })
      ON CREATE SET ps.required = 'id,name,status', ps.schemaDefinition = 'Схема свойств для серверов'
    MERGE (n)-[:HAS_PROPERTY_SCHEMA]->(ps)
    // Define properties for Server schema
    WITH ps
    UNWIND [
      { name: 'id', type: 'string', description: 'Уникальный идентификатор сервера', pattern: '^SRV[0-9]{6}$', required: true },
      { name: 'name', type: 'string', description: 'Имя сервера', required: true },
      { name: 'status', type: 'string', description: 'Текущий статус сервера', enumValues: 'Active,Inactive,Maintenance,Planned,Decommissioned', required: true },
      { name: 'type', type: 'string', description: 'Тип сервера', enumValues: 'Physical,Virtual,Container,Cloud', required: false },
      { name: 'manufacturer', type: 'string', description: 'Производитель оборудования', required: false },
      { name: 'model', type: 'string', description: 'Модель сервера', required: false }
    ] AS prop
    MERGE (p:PropertyDefinition { name: prop.name, entityTypeForSchema: 'Server' }) // Link definition to schema type+name
      ON CREATE SET p.type = prop.type, p.description = prop.description, p.pattern = prop.pattern, p.required = prop.required, p.enumValues = prop.enumValues
    MERGE (p)-[:DEFINES_PROPERTY]->(ps); // Corrected relationship direction
    "

    # Schema: Application
    execute_cypher "
    MATCH (n:Metadata:PropertySchemas)
    MERGE (ps:PropertySchema { entityType: 'Application' })
      ON CREATE SET ps.required = 'id,name,version,status', ps.schemaDefinition = 'Схема свойств для приложений'
    MERGE (n)-[:HAS_PROPERTY_SCHEMA]->(ps)
    WITH ps
    UNWIND [
      { name: 'id', type: 'string', description: 'Уникальный идентификатор приложения', pattern: '^APP[0-9]{6}$', required: true },
      { name: 'name', type: 'string', description: 'Название приложения', required: true },
      { name: 'version', type: 'string', description: 'Версия приложения', required: true },
      { name: 'status', type: 'string', description: 'Текущий статус приложения', enumValues: 'Active,Inactive,Maintenance,Development,Testing,Decommissioned', required: true },
      { name: 'vendor', type: 'string', description: 'Производитель/вендор приложения', required: false },
      { name: 'criticality', type: 'string', description: 'Уровень критичности приложения', enumValues: 'Low,Medium,High,Critical', required: false }
    ] AS prop
    MERGE (p:PropertyDefinition { name: prop.name, entityTypeForSchema: 'Application' })
      ON CREATE SET p.type = prop.type, p.description = prop.description, p.pattern = prop.pattern, p.required = prop.required, p.enumValues = prop.enumValues
    MERGE (p)-[:DEFINES_PROPERTY]->(ps);
    "

    # Schema: ITService
    execute_cypher "
    MATCH (n:Metadata:PropertySchemas)
    MERGE (ps:PropertySchema { entityType: 'ITService' })
      ON CREATE SET ps.required = 'id,name,status', ps.schemaDefinition = 'Схема свойств для ИТ-сервисов'
    MERGE (n)-[:HAS_PROPERTY_SCHEMA]->(ps)
    WITH ps
    UNWIND [
      { name: 'id', type: 'string', description: 'Уникальный идентификатор ИТ-сервиса', pattern: '^SVC[0-9]{6}$', required: true },
      { name: 'name', type: 'string', description: 'Название ИТ-сервиса', required: true },
      { name: 'status', type: 'string', description: 'Текущий статус ИТ-сервиса', enumValues: 'Active,Inactive,Maintenance,Development,Decommissioned', required: true },
      { name: 'criticality', type: 'string', description: 'Уровень критичности сервиса', enumValues: 'Low,Medium,High,Critical', required: false },
      { name: 'business_hours', type: 'string', description: 'Часы работы сервиса', required: false },
      { name: 'owner_id', type: 'string', description: 'ID владельца сервиса (ссылка на Person)', required: false }
    ] AS prop
    MERGE (p:PropertyDefinition { name: prop.name, entityTypeForSchema: 'ITService' })
      ON CREATE SET p.type = prop.type, p.description = prop.description, p.pattern = prop.pattern, p.required = prop.required, p.enumValues = prop.enumValues
    MERGE (p)-[:DEFINES_PROPERTY]->(ps);
    "

     # Schema: Person
    execute_cypher "
    MATCH (n:Metadata:PropertySchemas)
    MERGE (ps:PropertySchema { entityType: 'Person' })
      ON CREATE SET ps.required = 'id,name,status', ps.schemaDefinition = 'Схема свойств для сотрудников'
    MERGE (n)-[:HAS_PROPERTY_SCHEMA]->(ps)
    WITH ps
    UNWIND [
        { name: 'id', type: 'string', description: 'Уникальный идентификатор сотрудника', pattern: '^PERSON[0-9]{6}$', required: true },
        { name: 'name', type: 'string', description: 'ФИО сотрудника', required: true },
        { name: 'status', type: 'string', description: 'Статус сотрудника', enumValues: 'Active,Inactive,On Leave,Terminated', required: true },
        { name: 'email', type: 'string', description: 'Электронная почта', required: false },
        { name: 'phone', type: 'string', description: 'Телефон', required: false },
        { name: 'department_id', type: 'string', description: 'ID подразделения (ссылка на Department)', required: false }
    ] AS prop
    MERGE (p:PropertyDefinition { name: prop.name, entityTypeForSchema: 'Person' })
        ON CREATE SET p.type = prop.type, p.description = prop.description, p.pattern = prop.pattern, p.required = prop.required, p.enumValues = prop.enumValues
    MERGE (p)-[:DEFINES_PROPERTY]->(ps);
    "

    # Schema: Incident
    execute_cypher "
    MATCH (n:Metadata:PropertySchemas)
    MERGE (ps:PropertySchema { entityType: 'Incident' })
        ON CREATE SET ps.required = 'id,title,status,created_at', ps.schemaDefinition = 'Схема свойств для инцидентов'
    MERGE (n)-[:HAS_PROPERTY_SCHEMA]->(ps)
    WITH ps
    UNWIND [
        { name: 'id', type: 'string', description: 'Уникальный идентификатор инцидента', pattern: '^INC[0-9]{6}$', required: true },
        { name: 'title', type: 'string', description: 'Заголовок инцидента', required: true },
        { name: 'status', type: 'string', description: 'Статус инцидента', enumValues: 'New,In Progress,On Hold,Resolved,Closed,Cancelled', required: true },
        { name: 'created_at', type: 'datetime', description: 'Дата создания инцидента', required: true },
        { name: 'priority', type: 'string', description: 'Приоритет инцидента', enumValues: 'Low,Medium,High,Critical', required: false },
        { name: 'assigned_to', type: 'string', description: 'ID сотрудника, назначенного на инцидент (ссылка на Person)', required: false }
    ] AS prop
    MERGE (p:PropertyDefinition { name: prop.name, entityTypeForSchema: 'Incident' })
        ON CREATE SET p.type = prop.type, p.description = prop.description, p.pattern = prop.pattern, p.required = prop.required, p.enumValues = prop.enumValues
    MERGE (p)-[:DEFINES_PROPERTY]->(ps);
    "

    log_message "Создание схем атрибутов завершено."
}

# 6. Verify Structure (Basic Checks)
verify_structure() {
    log_message "--- [6/6] Проверка созданной структуры (Базовые запросы) ---"
    execute_cypher "MATCH (n:Metadata) RETURN labels(n) AS MetadataType, count(*) AS Count;"
    execute_cypher "MATCH (et:EntityTypeDefinition) RETURN et.category AS Category, count(et) AS EntityTypeCount ORDER BY Category;"
    execute_cypher "MATCH (rt:RelationshipTypeDefinition) RETURN rt.category AS Category, count(rt) AS RelationshipTypeCount ORDER BY Category;"
    execute_cypher "MATCH (ps:PropertySchema) RETURN ps.entityType AS EntityTypeWithSchema ORDER BY EntityTypeWithSchema;"
    log_message "Проверка завершена. Детали смотрите выше."
    log_message "Для просмотра ВСЕХ ограничений и индексов выполните 'SHOW CONSTRAINTS' и 'SHOW INDEXES' в Neo4j Browser или cypher-shell."
}


# --- Main Execution Flow ---

log_message "===================================================="
log_message ">>> Начало инициализации структуры CMDB v3.0 <<<"
log_message "===================================================="
log_message "Параметры подключения:"
log_message "  Хост: $NEO4J_HOST"
log_message "  Порт: $NEO4J_PORT"
log_message "  Пользователь: $NEO4J_USER"
log_message "----------------------------------------------------"

# Execute steps based on flags
if [ "$SKIP_CONSTRAINTS" = false ]; then create_constraints; else log_message "[1/6] Создание ограничений пропущено."; fi
echo "----------------------------------------------------"
if [ "$SKIP_INDEXES" = false ]; then create_indexes; else log_message "[2/6] Создание индексов пропущено."; fi
echo "----------------------------------------------------"
if [ "$SKIP_ENTITY_META" = false ]; then create_entity_metadata; else log_message "[3/6] Создание метаданных сущностей пропущено."; fi
echo "----------------------------------------------------"
if [ "$SKIP_RELATION_META" = false ]; then create_relationship_metadata; else log_message "[4/6] Создание метаданных отношений пропущено."; fi
echo "----------------------------------------------------"
if [ "$SKIP_PROP_SCHEMAS" = false ]; then create_property_schemas; else log_message "[5/6] Создание схем атрибутов пропущено."; fi
echo "----------------------------------------------------"
if [ "$SKIP_VERIFY" = false ]; then verify_structure; else log_message "[6/6] Финальная проверка пропущена."; fi
echo "----------------------------------------------------"

log_message "===================================================="
log_message ">>> Инициализация структуры CMDB завершена (с учетом флагов) <<<"
log_message "===================================================="

exit 0
