import json
import os
import secrets
from pathlib import Path
from typing import Optional, List, Dict
from pydantic import BaseModel

ROLES_FILE = Path(os.getenv("DATA_DIR", "/data")) / "roles.json"

class Role(BaseModel):
    username: str
    token: str
    allowed_tools: List[str]
    description: Optional[str] = None
    created_at: str

def _load_roles() -> Dict[str, Role]:
    """Загружает роли из файла"""
    if not ROLES_FILE.exists():
        return {}
    with open(ROLES_FILE) as f:
        raw = json.load(f)
    return {k: Role(**v) for k, v in raw.items()}

def _save_roles(roles: Dict[str, Role]) -> None:
    """Сохраняет роли в файл"""
    ROLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ROLES_FILE, "w") as f:
        json.dump({k: v.model_dump() for k, v in roles.items()}, f, indent=2)

def generate_token() -> str:
    """Генерирует безопасный токен"""
    return secrets.token_urlsafe(32)

def create_role(username: str, allowed_tools: List[str], token: Optional[str] = None, description: Optional[str] = None) -> Role:
    """Создает новую роль"""
    from datetime import datetime
    
    roles = _load_roles()
    
    # Проверяем, что username уникален
    if username in roles:
        raise ValueError(f"Role with username '{username}' already exists")
    
    # Генерируем токен если не передан
    if not token:
        token = generate_token()
    
    role = Role(
        username=username,
        token=token,
        allowed_tools=allowed_tools,
        description=description,
        created_at=datetime.utcnow().isoformat()
    )
    
    roles[username] = role
    _save_roles(roles)
    
    return role

def get_role(username: str) -> Optional[Role]:
    """Получает роль по username"""
    roles = _load_roles()
    return roles.get(username)

def get_role_by_token(token: str) -> Optional[Role]:
    """Получает роль по токену"""
    roles = _load_roles()
    for role in roles.values():
        if role.token == token:
            return role
    return None

def list_roles() -> List[Role]:
    """Возвращает список всех ролей"""
    return list(_load_roles().values())

def delete_role(username: str) -> bool:
    """Удаляет роль"""
    roles = _load_roles()
    if username not in roles:
        return False
    del roles[username]
    _save_roles(roles)
    return True

def update_role(username: str, allowed_tools: Optional[List[str]] = None, description: Optional[str] = None) -> Optional[Role]:
    """Обновляет роль"""
    roles = _load_roles()
    if username not in roles:
        return None
    
    role = roles[username]
    if allowed_tools is not None:
        role.allowed_tools = allowed_tools
    if description is not None:
        role.description = description
    
    roles[username] = role
    _save_roles(roles)
    
    return role
</contents>