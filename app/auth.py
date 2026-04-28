import os
import secrets
import logging
from fastapi import HTTPException, Header
from typing import Optional, List
from .models import AuthLevel
from . import role_manager

logger = logging.getLogger(__name__)

# Токены задаются через переменные окружения
USER_TOKEN = os.getenv("MCP_USER_TOKEN", "")
if not USER_TOKEN:
    USER_TOKEN = secrets.token_urlsafe(32)
ADMIN_TOKEN = os.getenv("MCP_ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    ADMIN_TOKEN = secrets.token_urlsafe(32)
WEB_UI_TOKEN = os.getenv("WEB_UI_TOKEN", "")
if not WEB_UI_TOKEN:
    WEB_UI_TOKEN = secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Logging Startup Info
# ---------------------------------------------------------------------------
def print_startup_info():
    """Выводит информацию о токенах и ролях при старте"""
    print("\n" + "="*60)
    print("🚀 DOCKER MCP SERVER STARTED")
    print("="*60)
    print("\n📋 BUILT-IN TOKENS:")
    print(f"  🔑 USER_TOKEN:   {USER_TOKEN}")
    print(f"     Endpoint: /mcp/user")
    print(f"  🔑 ADMIN_TOKEN:  {ADMIN_TOKEN}")
    print(f"     Endpoint: /mcp/admin")
    print(f"  🔑 WEB_UI_TOKEN: {WEB_UI_TOKEN}")
    print(f"     Endpoint: / (Web UI)")
    
    # Выводим информацию о пользовательских ролях
    roles = role_manager.list_roles()
    if roles:
        print("\n🎭 CUSTOM ROLES:")
        for role in roles:
            print(f"  👤 {role.username}")
            print(f"     Token: {role.token}")
            print(f"     Endpoint: /mcp/{role.username}")
            print(f"     Tools: {', '.join(role.allowed_tools)}")
            if role.description:
                print(f"     Description: {role.description}")
            print()
    else:
        print("\n🎭 CUSTOM ROLES: None (create via API)")
    
    print("\n" + "="*60)
    print("⚠️  IMPORTANT: BACKUP YOUR ENCRYPTION KEYS!")
    print("="*60)
    print("All passwords and SSH keys are encrypted.")
    print("To backup: GET /api/crypto/backup-instructions")
    print("Without backup, data loss on container recreation!")
    print("="*60 + "\n")

# Вызываем при импорте модуля
print_startup_info()


# Какие инструменты доступны каждому уровню
TOOLS_BY_LEVEL: dict[AuthLevel, list[str]] = {
    AuthLevel.USER: [
        "list_servers",
        "list_containers",
        "view_logs",
        "read_file",
    ],
    AuthLevel.ADMIN: [
        "list_servers",
        "list_containers",
        "start_container",
        "stop_container",
        "add_server",
        "view_logs",
        "read_file",
        "exec_command",
    ],
}


def get_auth_level(authorization: Optional[str]) -> AuthLevel:
    """Определяет уровень доступа по токену из заголовка Authorization: Bearer <token>"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    if token == ADMIN_TOKEN:
        return AuthLevel.ADMIN
    elif token == USER_TOKEN:
        return AuthLevel.USER
    else:
        # Проверяем динамические роли
        role = role_manager.get_role_by_token(token)
        if role:
            # Динамические роли считаются USER уровнем, но с кастомными инструментами
            return AuthLevel.USER
        raise HTTPException(status_code=403, detail="Invalid token")


def get_allowed_tools(level: AuthLevel, token: Optional[str] = None) -> list[str]:
    """Возвращает список разрешенных инструментов для уровня доступа или роли"""
    # Если передан токен, проверяем динамические роли
    if token:
        role = role_manager.get_role_by_token(token)
        if role:
            return role.allowed_tools
    
    return TOOLS_BY_LEVEL.get(level, [])


def check_tool_access(level: AuthLevel, tool_name: str) -> None:
    """Бросает исключение если инструмент недоступен для данного уровня"""
    if tool_name not in get_allowed_tools(level):
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool_name}' is not available for your access level"
        )


def verify_web_token(authorization: Optional[str]) -> None:
    """Проверка токена для Web UI"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.removeprefix("Bearer ").strip()
    # Web UI принимает и admin и webui токен
    if token not in (ADMIN_TOKEN, WEB_UI_TOKEN):
        raise HTTPException(status_code=403, detail="Forbidden")