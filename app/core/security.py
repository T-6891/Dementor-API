import logging
from typing import Optional, List

from fastapi import Depends, HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from app.core.config import settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

class APIKeyValidator:
    """Валидатор API-ключей"""
    
    def __init__(self, required_permissions: List[str] = None):
        self.required_permissions = required_permissions or []
    
    async def __call__(self, request: Request, api_key: str = Security(API_KEY_HEADER)) -> str:
        """Валидация API-ключа"""
        if not api_key:
            logger.warning("Отсутствует API-ключ в заголовке запроса")
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Требуется API-ключ",
            )
        
        # Проверяем API-ключ
        api_key_info = self._validate_api_key(api_key)
        if not api_key_info:
            logger.warning(f"Невалидный API-ключ: {api_key}")
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Невалидный API-ключ",
            )
        
        # Проверяем права доступа
        if self.required_permissions and not all(
            perm in api_key_info.permissions for perm in self.required_permissions
        ):
            logger.warning(
                f"Недостаточно прав для API-ключа {api_key_info.client_id}. "
                f"Требуются: {self.required_permissions}, Имеются: {api_key_info.permissions}"
            )
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции",
            )
        
        # Добавляем клиента в запрос для дальнейшего использования
        request.state.client_id = api_key_info.client_id
        return api_key_info.client_id
    
    def _validate_api_key(self, api_key: str) -> Optional[dict]:
        """Проверить валидность API-ключа"""
        for key_info in settings.settings.api_keys:
            if key_info.key == api_key:
                return key_info
        return None

# Зависимости для различных уровней доступа
get_api_key = APIKeyValidator()
require_read_access = APIKeyValidator(required_permissions=["read"])
require_write_access = APIKeyValidator(required_permissions=["write"])
require_admin_access = APIKeyValidator(required_permissions=["admin"])