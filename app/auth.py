import os
import secrets
from fastapi import HTTPException, Header
from typing import Optional
from .models import AuthLevel

# Токены задаются через переменные окружения
USER_TOKEN = os.getenv("MCP_USER_TOKEN", "user-token-change-me")
if not USER_TOKEN:
    USER_TOKEN = secrets.token_urlsafe(32)
ADMIN_TOKEN = os.getenv("MCP_ADMIN_TOKEN", "admin-token-change-me")
if not ADMIN_TOKEN:
    ADMIN_TOKEN = secrets.token_urlsafe(32)
WEB_UI_TOKEN = os.getenv("WEB_UI_TOKEN", "webui-token-change-me")
if not WEB_UI_TOKEN:
    WEB_UI_TOKEN = secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Logging Startup Info
# ---------------------------------------------------------------------------
print("\n" + "="*50)
print("🚀 DOCKER MCP SERVER STARTED")
#print(f"🌍 URL: http://{SERVER_HOST}:{SERVER_PORT}/mcp")
print(f"🔑 AUTH USER_TOKEN: {USER_TOKEN if USER_TOKEN else 'DISABLED'}")
print(f"🔑 AUTH ADMIN_TOKEN: {ADMIN_TOKEN if ADMIN_TOKEN else 'DISABLED'}")
print(f"🔑 AUTH WEB_UI_TOKEN: {WEB_UI_TOKEN if WEB_UI_TOKEN else 'DISABLED'}")
print("="*50 + "\n")


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
        raise HTTPException(status_code=403, detail="Invalid token")


def get_allowed_tools(level: AuthLevel) -> list[str]:
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