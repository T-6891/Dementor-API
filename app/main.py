import logging
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import neo4j_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Создаем экземпляр FastAPI
app = FastAPI(
    title=settings.settings.app_name,
    description="API для управления CMDB на базе Neo4j",
    version=settings.settings.version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Добавляем middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене следует указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Обработка исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    logger.error(f"Необработанное исключение: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"}
    )

# Проверка подключения к Neo4j при старте
@app.on_event("startup")
async def startup_db_client():
    """Инициализация подключения к Neo4j при старте приложения"""
    try:
        if neo4j_manager.check_connection():
            logger.info("Успешное подключение к Neo4j")
        else:
            logger.error("Не удалось подключиться к Neo4j")
    except Exception as e:
        logger.error(f"Ошибка при подключении к Neo4j: {str(e)}")

# Закрытие подключения к Neo4j при остановке
@app.on_event("shutdown")
async def shutdown_db_client():
    """Закрытие подключения к Neo4j при остановке приложения"""
    try:
        neo4j_manager.close()
        logger.info("Соединение с Neo4j закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с Neo4j: {str(e)}")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Главная страница
@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница"""
    try:
        with open(os.path.join(os.path.dirname(__file__), "static", "index.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        logger.error(f"Ошибка при открытии index.html: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при открытии главной страницы")

# Добавляем маршруты API
app.include_router(api_router, prefix=settings.settings.api_prefix)

# Точка входа для запуска через uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.settings.debug
    )