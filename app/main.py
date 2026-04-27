import logging
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import get_auth_level, get_allowed_tools, check_tool_access, verify_web_token
from .docker_tools import TOOL_SCHEMAS, execute_tool
from .models import MCPRequest, MCPResponse, AuthLevel, AddServerRequest, CreateRoleRequest, UpdateRoleRequest
from . import server_manager, role_manager
from .security import sanitize_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Docker MCP Hub", version="0.1.0")


# ── Helpers ──────────────────────────────────────────────────────────────────

def mcp_error(id_, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def mcp_result(id_, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


# ── MCP handler (shared logic) ───────────────────────────────────────────────

async def handle_mcp(request: Request, auth_level: AuthLevel, token: Optional[str] = None) -> JSONResponse:
    allowed = get_allowed_tools(auth_level, token)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(mcp_error(None, -32700, "Parse error"))

    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params") or {}

    logger.info(f"[{auth_level}] method={method}")

    # ── initialize ────────────────────────────────────────────────────────────
    if method == "initialize":
        return JSONResponse(mcp_result(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "docker-mcp-hub", "version": "0.1.0"},
        }))

    # ── notifications/initialized (no response needed) ────────────────────────
    if method == "notifications/initialized":
        return JSONResponse(status_code=204, content=None)

    # ── tools/list ────────────────────────────────────────────────────────────
    if method == "tools/list":
        tools = [TOOL_SCHEMAS[name] for name in allowed if name in TOOL_SCHEMAS]
        return JSONResponse(mcp_result(req_id, {"tools": tools}))

    # ── tools/call ────────────────────────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments") or {}

        if tool_name not in allowed:
            return JSONResponse(mcp_error(req_id, -32603,
                f"Tool '{tool_name}' is not available for your access level"))

        try:
            result = execute_tool(tool_name, tool_args)
            return JSONResponse(mcp_result(req_id, {
                "content": [{"type": "text", "text": str(result)}],
                "isError": False,
            }))
        except ValueError as e:
            return JSONResponse(mcp_error(req_id, -32602, str(e)))
        except Exception as e:
            logger.error(f"Tool error: {e}", exc_info=True)
            return JSONResponse(mcp_error(req_id, -32603, f"Internal error: {e}"))

    return JSONResponse(mcp_error(req_id, -32601, f"Method not found: {method}"))


# ── MCP routes ───────────────────────────────────────────────────────────────

@app.post("/mcp/user")
async def mcp_user(request: Request, authorization: Optional[str] = Header(None)):
    level = get_auth_level(authorization)
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    # User path принимает только уровень user (не admin)
    if level != AuthLevel.USER:
        raise HTTPException(403, "This endpoint is for user tokens only")
    return await handle_mcp(request, AuthLevel.USER, token)


@app.post("/mcp/admin")
async def mcp_admin(request: Request, authorization: Optional[str] = Header(None)):
    level = get_auth_level(authorization)
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    if level != AuthLevel.ADMIN:
        raise HTTPException(403, "This endpoint requires admin token")
    return await handle_mcp(request, AuthLevel.ADMIN, token)


@app.post("/mcp/{username}")
async def mcp_dynamic_role(username: str, request: Request, authorization: Optional[str] = Header(None)):
    """Динамический MCP эндпоинт для пользовательских ролей"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    
    token = authorization.removeprefix("Bearer ").strip()
    
    # Проверяем, что роль существует и токен совпадает
    role = role_manager.get_role(username)
    if not role:
        raise HTTPException(404, f"Role '{username}' not found")
    
    if role.token != token:
        raise HTTPException(403, "Invalid token for this role")
    
    # Обрабатываем запрос с правами USER, но с кастомными инструментами
    return await handle_mcp(request, AuthLevel.USER, token)


# ── Role Management API ─────────────────────────────────────────────────────

@app.post("/api/roles")
async def api_create_role(req: CreateRoleRequest, authorization: Optional[str] = Header(None)):
    """Создает новую роль (только для admin)"""
    verify_web_token(authorization)
    role = role_manager.create_role(
        username=req.username,
        allowed_tools=req.allowed_tools,
        token=req.token,
        description=req.description
    )
    result = role.model_dump()
    
    # Логируем информацию о новой роли
    logger.info(f"\n{'='*60}")
    logger.info(f"🎭 NEW ROLE CREATED: {role.username}")
    logger.info(f"🔑 Token: {role.token}")
    logger.info(f"🔧 Allowed tools: {', '.join(role.allowed_tools)}")
    logger.info(f"🌐 MCP Endpoint: /mcp/{role.username}")
    if role.description:
        logger.info(f"📝 Description: {role.description}")
    logger.info(f"{'='*60}\n")
    
    return sanitize_response(result)


@app.get("/api/roles")
async def api_list_roles(authorization: Optional[str] = Header(None)):
    """Список всех ролей (только для admin)"""
    verify_web_token(authorization)
    roles = role_manager.list_roles()
    result = [r.model_dump() for r in roles]
    return sanitize_response(result)


@app.get("/api/roles/{username}")
async def api_get_role(username: str, authorization: Optional[str] = Header(None)):
    """Получить информацию о роли (только для admin)"""
    verify_web_token(authorization)
    role = role_manager.get_role(username)
    if not role:
        raise HTTPException(404, "Role not found")
    return sanitize_response(role.model_dump())


@app.put("/api/roles/{username}")
async def api_update_role(username: str, req: UpdateRoleRequest, authorization: Optional[str] = Header(None)):
    """Обновить роль (только для admin)"""
    verify_web_token(authorization)
    role = role_manager.update_role(
        username=username,
        allowed_tools=req.allowed_tools,
        description=req.description
    )
    if not role:
        raise HTTPException(404, "Role not found")
    return sanitize_response(role.model_dump())


@app.delete("/api/roles/{username}")
async def api_delete_role(username: str, authorization: Optional[str] = Header(None)):
    """Удалить роль (только для admin)"""
    verify_web_token(authorization)
    ok = role_manager.delete_role(username)
    if not ok:
        raise HTTPException(404, "Role not found")
    return {"message": "Role deleted"}


# ── Web UI API ───────────────────────────────────────────────────────────────

@app.get("/api/servers")
async def api_list_servers(authorization: Optional[str] = Header(None)):
    verify_web_token(authorization)
    servers = server_manager.list_servers()
    result = [s.model_dump(exclude={"password"}) for s in servers]
    return sanitize_response(result)


@app.post("/api/servers")
async def api_add_server(req: AddServerRequest, authorization: Optional[str] = Header(None)):
    verify_web_token(authorization)
    cfg = server_manager.add_server(req)
    result = cfg.model_dump(exclude={"password"})
    return sanitize_response(result)


@app.delete("/api/servers/{server_id}")
async def api_delete_server(server_id: str, authorization: Optional[str] = Header(None)):
    verify_web_token(authorization)
    ok = server_manager.remove_server(server_id)
    if not ok:
        raise HTTPException(404, "Server not found")
    return {"message": "Deleted"}


# ── Web UI ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def web_ui():
    from pathlib import Path
    html_path = Path(__file__).parent / "web" / "index.html"
    return HTMLResponse(content=html_path.read_text())


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}