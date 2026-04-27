from pydantic import BaseModel
from typing import Optional, Literal
from enum import Enum


class AuthLevel(str, Enum):
    USER = "user"
    ADMIN = "admin"


class ServerAuthType(str, Enum):
    PASSWORD = "password"
    KEY_PATH = "key_path"
    GENERATE_KEY = "generate_key"


class ServerConfig(BaseModel):
    id: str
    name: str
    host: str
    port: int = 22
    username: str
    auth_type: ServerAuthType
    # Заполняется в зависимости от auth_type
    password: Optional[str] = None       # для PASSWORD
    key_path: Optional[str] = None       # для KEY_PATH
    generated_key_name: Optional[str] = None  # для GENERATE_KEY
    description: Optional[str] = None
    tags: list[str] = []


class AddServerRequest(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str
    auth_type: ServerAuthType
    password: Optional[str] = None
    key_path: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = []


class CreateRoleRequest(BaseModel):
    username: str
    allowed_tools: list[str]
    token: Optional[str] = None
    description: Optional[str] = None


class UpdateRoleRequest(BaseModel):
    allowed_tools: Optional[list[str]] = None
    description: Optional[str] = None


class ContainerInfo(BaseModel):
    id: str
    name: str
    image: str
    status: str
    state: str
    ports: str


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str | int] = None
    method: str
    params: Optional[dict] = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str | int] = None
    result: Optional[dict] = None
    error: Optional[dict] = None