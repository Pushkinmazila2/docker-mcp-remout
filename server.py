import os
import json
import secrets
import docker
import docker.errors
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse


SERVER_HOST = os.environ.get("SERVER_HOST", "your-server")
SERVER_PORT = os.environ.get("SERVER_PORT", "8000")

AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")
if not AUTH_TOKEN:
    AUTH_TOKEN = secrets.token_urlsafe(32)

_whitelist_env = os.environ.get("EXEC_WHITELIST", "")
EXEC_WHITELIST: list[str] | None = (
    [c.strip() for c in _whitelist_env.split(",") if c.strip()]
    if _whitelist_env else None  
)

_safe_paths_raw = os.environ.get("SAFE_MOUNT_DIR", "/app/data,/var/log/app")
SAFE_MOUNT_PATHS = [
    os.path.realpath(p.strip()) 
    for p in _safe_paths_raw.split(",") if p.strip()
]


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------
class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/"):
            return await call_next(request)
        
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or \
           not secrets.compare_digest(auth_header[7:], AUTH_TOKEN):
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing token"},
            )
        return await call_next(request)
        
# ---------------------------------------------------------------------------
# Logging Startup Info
# ---------------------------------------------------------------------------
print("\n" + "="*50)
print("🚀 DOCKER MCP SERVER STARTED")
print(f"🌍 URL: http://{SERVER_HOST}:{SERVER_PORT}/mcp")
print(f"🔑 AUTH TOKEN: {AUTH_TOKEN if AUTH_TOKEN else 'DISABLED'}")
print(f"🛡️  WHITELIST: {', '.join(EXEC_WHITELIST) if EXEC_WHITELIST else 'ALL'}")
print("="*50 + "\n")

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "docker-manager",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)


def client() -> docker.DockerClient:
    return docker.from_env()


# ---------------------------------------------------------------------------
# Web index page
# ---------------------------------------------------------------------------
@mcp.custom_route("/", methods=["GET"])
async def index(request: Request):
    auth_line = f'"Authorization": "Bearer {AUTH_TOKEN}"' if AUTH_TOKEN else "# no auth token set"
    whitelist_info = (
        f"<code>{', '.join(EXEC_WHITELIST)}</code>"
        if EXEC_WHITELIST
        else "<em>all commands allowed</em>"
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Docker MCP Server</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f1117; color: #e2e8f0; min-height: 100vh; padding: 40px 20px; }}
  .container {{ max-width: 860px; margin: 0 auto; }}
  h1 {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 4px; }}
  h1 span {{ color: #3b82f6; }}
  .subtitle {{ color: #64748b; margin-bottom: 32px; font-size: 0.95rem; }}
  .status {{ display: inline-flex; align-items: center; gap: 6px; background: #1a2235;
             border: 1px solid #22c55e33; border-radius: 999px; padding: 4px 12px;
             font-size: 0.8rem; color: #22c55e; margin-bottom: 32px; }}
  .dot {{ width: 7px; height: 7px; border-radius: 50%; background: #22c55e;
          animation: pulse 2s infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity:1 }} 50% {{ opacity:.4 }} }}
  .card {{ background: #1a1f2e; border: 1px solid #2d3548; border-radius: 12px;
           padding: 24px; margin-bottom: 20px; }}
  .card h2 {{ font-size: 1rem; font-weight: 600; margin-bottom: 16px; color: #94a3b8;
              text-transform: uppercase; letter-spacing: .06em; font-size: .75rem; }}
  pre {{ background: #0d1117; border: 1px solid #2d3548; border-radius: 8px;
         padding: 16px; overflow-x: auto; font-size: .82rem; line-height: 1.6;
         color: #c9d1d9; }}
  .key {{ color: #79c0ff; }}
  .val {{ color: #a5d6ff; }}
  .str {{ color: #a8ff78; }}
  .comment {{ color: #64748b; }}
  .tools-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr));
                 gap: 8px; }}
  .tool {{ background: #0d1117; border: 1px solid #2d3548; border-radius: 8px;
           padding: 8px 12px; font-size: .82rem; font-family: monospace; color: #7dd3fc; }}
  .section-label {{ font-size: .7rem; color: #475569; text-transform: uppercase;
                    letter-spacing: .1em; margin: 16px 0 8px; }}
  .tag {{ display: inline-block; background: #1e293b; border: 1px solid #334155;
          border-radius: 4px; padding: 2px 8px; font-size: .75rem; color: #94a3b8;
          margin: 2px; }}
  a {{ color: #3b82f6; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="container">
  <h1>Docker <span>MCP</span> Server</h1>
  <p class="subtitle">Model Context Protocol server for Docker management</p>
  <div class="status"><span class="dot"></span> Running on {SERVER_HOST}:{SERVER_PORT}</div>
  
  <div class="card">
    <h2>Connection VSCode (Continue)</h2>
    <pre><span class="comment">// .continue/mcpServers/DockerMCP.yaml</span>
<span class="key">name</span>: <span class="str">DockerMCP</span>
<span class="key">version</span>: <span class="str">0.0.1</span>
<span class="key">schema</span>: <span class="str">v1</span>
<span class="key">mcpServers</span>:
  - <span class="key">name</span>: <span class="str">"DockerMCP"</span>
    <span class="key">type</span>: <span class="str">"streamable-http"</span>
    <span class="key">url</span>: <span class="str">"http://{SERVER_HOST}:{SERVER_PORT}/mcp"</span>
    <span class="key">requestOptions</span>:
      <span class="key">headers</span>:
        <span class="key">Authorization</span>: <span class="str">"Bearer your-token"</span></pre>
</div>

  <div class="card">
    <h2>Connection Claude Desktop</h2>
    <pre><span class="comment">// claude_desktop_config.json</span>
{{
  <span class="key">"mcpServers"</span>: {{
    <span class="key">"docker-remote"</span>: {{
      <span class="key">"type"</span>: <span class="str">"http"</span>,
      <span class="key">"url"</span>: <span class="str">"http://{SERVER_HOST}:{SERVER_PORT}/mcp"</span>,
      <span class="key">"headers"</span>: {{
        <span class="key">"Authorization"</span>: <span class="str">"Bearer your-token"</span>
      }}
    }}
  }}
}}</pre>
  </div>

  <div class="card">
    <h2>Connection Claude Code (CLI)</h2>
    <pre>claude mcp add --transport http docker-remote \\
  http://{SERVER_HOST}:{SERVER_PORT}/mcp \\
  --header <span class="str">"Authorization: Bearer your-token"</span></pre>
  </div>

  <div class="card">
    <h2>Connection Cursor / Windsurf</h2>
    <pre><span class="comment">// ~/.cursor/mcp.json</span>
{{
  <span class="key">"mcpServers"</span>: {{
    <span class="key">"docker-remote"</span>: {{
      <span class="key">"type"</span>: <span class="str">"streamable-http"</span>,
      <span class="key">"url"</span>: <span class="str">"http://{SERVER_HOST}:{SERVER_PORT}/mcp"</span>,
      <span class="key">"headers"</span>: {{
        <span class="key">"Authorization"</span>: <span class="str">"Bearer your-token"</span>
      }}
    }}
  }}
}}</pre>
  </div>


  <div class="card">
    <h2>Available Tools</h2>
    <div class="section-label">Containers</div>
    <div class="tools-grid">
    <div class="tool">MINI_list_of_containers</div>
      <div class="tool">list_containers</div>
      <div class="tool">create_container</div>
      <div class="tool">run_container</div>
      <div class="tool">recreate_container</div>
      <div class="tool">start_container</div>
      <div class="tool">stop_container</div>
      <div class="tool">remove_container</div>
      <div class="tool">fetch_container_logs</div>
      <div class="tool">get_container_stats</div>
      <div class="tool">list_resource_limits</div>
      <div class="tool">edit_resource_limits</div>
      <div class="tool">exec_container</div>
    </div>
    <div class="section-label">Images</div>
    <div class="tools-grid">
      <div class="tool">list_images</div>
      <div class="tool">pull_image</div>
      <div class="tool">push_image</div>
      <div class="tool">build_image</div>
      <div class="tool">remove_image</div>
    </div>
    <div class="section-label">Networks</div>
    <div class="tools-grid">
      <div class="tool">list_networks</div>
      <div class="tool">create_network</div>
      <div class="tool">remove_network</div>
    </div>
    <div class="section-label">Volumes</div>
    <div class="tools-grid">
      <div class="tool">list_volumes</div>
      <div class="tool">create_volume</div>
      <div class="tool">remove_volume</div>
    </div>
  </div>

  <div class="card">
    <h2>Exec Whitelist</h2>
    <p style="font-size:.875rem; color:#94a3b8;">
      Commands allowed inside containers via <code style="color:#7dd3fc">exec_container</code>:<br><br>
      {whitelist_info}<br><br>
      Set via env: <code style="color:#7dd3fc">EXEC_WHITELIST=ls,ps,df,top</code>
    </p>
  </div>

  <div class="card">
    <h2>Health Check</h2>
    <pre>curl http://{SERVER_HOST}:{SERVER_PORT}/health
<span class="comment">{{"status": "ok"}}</span></pre>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request):
    return JSONResponse({"status": "ok"})


# ===========================================================================
# validate_volumes
# ===========================================================================

def validate_volumes(volumes: dict | None) -> dict | None:
    if not volumes:
        return None
    
    for host_path in volumes.keys():
        if host_path.strip() in ("/", ".", "./", ".."):
            raise ValueError("Mounting '/' or '.' is strictly forbidden for security reasons.")
            
        if host_path.startswith("/") or host_path.startswith("."):
            real_path = os.path.realpath(host_path)
            is_safe = any(real_path.startswith(safe_path) for safe_path in SAFE_MOUNT_PATHS)
            
            if not is_safe:
                allowed_str = ", ".join(SAFE_MOUNT_PATHS)
                raise ValueError(
                    f"Access denied to '{host_path}'. Mounting is only allowed from: {allowed_str}"
                )
    return volumes


# ===========================================================================
# TOOLS - Containers
# ===========================================================================

@mcp.tool()
def get_system_info() -> dict:
    """Get host system capacity: CPU, RAM, and Disk space."""
    import shutil
    import psutil

    vm = psutil.virtual_memory()
    du = shutil.disk_usage("/")
    
    return {
        "cpu_count": psutil.cpu_count(),
        "cpu_load_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total_gb": round(vm.total / (1024**3), 1),
            "available_gb": round(vm.available / (1024**3), 1),
            "percent_used": vm.percent
        },
        "disk": {
            "total_gb": round(du.total / (1024**3), 1),
            "free_gb": round(du.free / (1024**3), 1)
        },
        "docker_version": client().version().get("Version")
    }

@mcp.tool()
def list_containers_brief() -> str:
    """list of containers"""
    #Ultra-compact list of containers for token saving.
    containers = client().containers.list(all=True)
    lines = [f"{c.short_id} | {c.name[:20]} | {c.status} | {c.image.tags[0] if c.image.tags else 'no-tag'}" 
             for c in containers]
    return "ID | NAME | STATUS | IMAGE\n" + "\n".join(lines)

@mcp.tool()
def list_containers(all: bool = False) -> list[dict]:
    """FULL List containers. all=True includes stopped ones."""
    containers = client().containers.list(all=all)
    result = []
    for c in containers:
        result.append({
            "id": c.short_id,
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "status": c.status,
            "ports": c.ports,
            "created": c.attrs["Created"][:19].replace("T", " "),
        })
    return result


@mcp.tool()
def create_container(
    image: str,
    name: str | None = None,
    command: str | None = None,
    ports: dict | None = None,
    environment: dict | None = None,
    volumes: dict | None = None,
    network: str | None = None,
    restart_policy: str | None = None,
    detach: bool = True,
) -> dict:
    """
    Args:
        image: Docker image name (e.g. nginx:latest)
        name: Optional container name
        command: Override default command
        ports: Port bindings, e.g. {"80/tcp": 8080}
        environment: Env vars dict, e.g. {"FOO": "bar"}
        volumes: Volume mounts, e.g. {"/host/path": {"bind": "/container/path", "mode": "rw"}}
        network: Network name to attach
        restart_policy: One of: no, always, on-failure, unless-stopped
        detach: Run in background (default True)
    SECURITY: Only volumes from allowed paths are permitted.
    """
    create_container.__doc__ = f"Create a container. Allowed mount paths: {', '.join(SAFE_MOUNT_PATHS)}"
    

    safe_volumes = validate_volumes(volumes)
    
    kwargs: dict = {"image": image, "detach": detach}
    if name:        kwargs["name"] = name
    if command:     kwargs["command"] = command
    if ports:       kwargs["ports"] = ports
    if environment: kwargs["environment"] = environment
    if safe_volumes: kwargs["volumes"] = safe_volumes
    if network:     kwargs["network"] = network
    if restart_policy:
        kwargs["restart_policy"] = {"Name": restart_policy}

    c = client().containers.create(**kwargs)
    return {"id": c.short_id, "name": c.name, "status": c.status}

@mcp.tool()
def run_container(
    image: str,
    name: str | None = None,
    command: str | None = None,
    ports: dict | None = None,
    environment: dict | None = None,
    volumes: dict | None = None,
    network: str | None = None,
    restart_policy: str | None = None,
    remove: bool = False,
) -> dict:
    """
    Create and start a container.
    Args:
        image: Docker image name
        name: Optional container name
        command: Override default command
        ports: Port bindings, e.g. {"80/tcp": 8080}
        environment: Env vars dict
        volumes: Volume mounts dict
        network: Network name
        restart_policy: no / always / on-failure / unless-stopped
        remove: Auto-remove container when it exits
    SECURITY: Only volumes from allowed paths are permitted.
    """
    run_container.__doc__ = f"Run a container. Allowed mount paths: {', '.join(SAFE_MOUNT_PATHS)}"

    safe_volumes = validate_volumes(volumes)
    
    kwargs: dict = {"image": image, "detach": True, "remove": remove}
    if name:        kwargs["name"] = name
    if command:     kwargs["command"] = command
    if ports:       kwargs["ports"] = ports
    if environment: kwargs["environment"] = environment
    if safe_volumes: kwargs["volumes"] = safe_volumes
    if network:     kwargs["network"] = network
    if restart_policy:
        kwargs["restart_policy"] = {"Name": restart_policy}

    c = client().containers.run(**kwargs)
    return {"id": c.short_id, "name": c.name, "status": c.status}


@mcp.tool()
def recreate_container(container_name: str, pull_new_image: bool = False) -> dict:
    """
    Stop, remove and re-create a container with the same config (docker compose recreate style).

    Args:
        container_name: Container name or ID
        pull_new_image: Pull latest image before recreating
    """
    dc = client()
    c = dc.containers.get(container_name)
    attrs = c.attrs

    image = attrs["Config"]["Image"]
    name  = attrs["Name"].lstrip("/")
    config = attrs["Config"]
    host_config = attrs["HostConfig"]

    if pull_new_image:
        dc.images.pull(image)

    c.stop()
    c.remove()

    kwargs: dict = {
        "image": image,
        "name": name,
        "detach": True,
        "environment": config.get("Env") or [],
        "command": config.get("Cmd"),
        "ports": {p: host_config["PortBindings"].get(p) for p in (config.get("ExposedPorts") or {})},
        "restart_policy": host_config.get("RestartPolicy") or {"Name": "no"},
        "volumes": host_config.get("Binds") or [],
    }

    new_c = dc.containers.run(**kwargs)
    return {"id": new_c.short_id, "name": new_c.name, "status": new_c.status}


@mcp.tool()
def start_container(container_name: str) -> dict:
    """Start a stopped container."""
    c = client().containers.get(container_name)
    c.start()
    c.reload()
    return {"id": c.short_id, "name": c.name, "status": c.status}


@mcp.tool()
def stop_container(container_name: str, timeout: int = 10) -> dict:
    """
    Stop a running container.

    Args:
        container_name: Container name or ID
        timeout: Seconds to wait before killing (default 10)
    """
    c = client().containers.get(container_name)
    c.stop(timeout=timeout)
    c.reload()
    return {"id": c.short_id, "name": c.name, "status": c.status}


@mcp.tool()
def remove_container(container_name: str, force: bool = False, remove_volumes: bool = False) -> dict:
    """
    Remove a container.

    Args:
        container_name: Container name or ID
        force: Force remove even if running
        remove_volumes: Also remove associated anonymous volumes
    """
    c = client().containers.get(container_name)
    name = c.name
    cid  = c.short_id
    c.remove(force=force, v=remove_volumes)
    return {"id": cid, "name": name, "removed": True}


@mcp.tool()
def fetch_container_logs(
    container_name: str,
    tail: int = 100,
    since: str | None = None,
    timestamps: bool = False,
) -> str:
    """
    Fetch container logs.

    Args:
        container_name: Container name or ID
        tail: Number of lines from the end (default 100)
        since: Show logs since timestamp, e.g. "2024-01-01T00:00:00"
        timestamps: Prefix each line with timestamp
    """
    c = client().containers.get(container_name)
    kwargs: dict = {"tail": tail, "timestamps": timestamps, "stream": False}
    if since:
        kwargs["since"] = since
    logs = c.logs(**kwargs)
    return logs.decode("utf-8", errors="replace")


@mcp.tool()
def get_container_stats(container_name: str) -> dict:
    """Get live CPU and memory stats for a container."""
    c = client().containers.get(container_name)
    s = c.stats(stream=False)

    cpu_delta    = s["cpu_stats"]["cpu_usage"]["total_usage"] - s["precpu_stats"]["cpu_usage"]["total_usage"]
    system_delta = s["cpu_stats"]["system_cpu_usage"] - s["precpu_stats"]["system_cpu_usage"]
    num_cpus     = s["cpu_stats"].get("online_cpus", 1)
    cpu_pct      = (cpu_delta / system_delta) * num_cpus * 100.0 if system_delta > 0 else 0.0

    mem_usage = s["memory_stats"].get("usage", 0)
    mem_limit = s["memory_stats"].get("limit", 1)

    return {
        "name":             c.name,
        "status":           c.status,
        "cpu_percent":      round(cpu_pct, 2),
        "memory_usage_mb":  round(mem_usage / 1024 / 1024, 1),
        "memory_limit_mb":  round(mem_limit / 1024 / 1024, 1),
        "memory_percent":   round((mem_usage / mem_limit) * 100, 2),
    }


@mcp.tool()
def list_resource_limits(container_name: str) -> dict:
    """
    Show current CPU and memory resource limits for a container.

    Args:
        container_name: Container name or ID
    """
    c = client().containers.get(container_name)
    hc = c.attrs["HostConfig"]
    return {
        "name":                c.name,
        "cpu_shares":          hc.get("CpuShares"),
        "cpu_period":          hc.get("CpuPeriod"),
        "cpu_quota":           hc.get("CpuQuota"),
        "cpuset_cpus":         hc.get("CpusetCpus"),
        "memory_limit_bytes":  hc.get("Memory"),
        "memory_swap_bytes":   hc.get("MemorySwap"),
        "memory_reservation":  hc.get("MemoryReservation"),
        "nano_cpus":           hc.get("NanoCpus"),
    }


@mcp.tool()
def edit_resource_limits(
    container_name: str,
    memory: str | None = None,
    memory_swap: str | None = None,
    cpu_shares: int | None = None,
    nano_cpus: float | None = None,
    cpuset_cpus: str | None = None,
) -> dict:
    """
    Update CPU / memory limits of a running container (no restart needed).

    Args:
        container_name: Container name or ID
        memory: Memory limit, e.g. "512m", "2g"  (0 = unlimited)
        memory_swap: Swap limit, e.g. "1g"  (-1 = unlimited)
        cpu_shares: Relative CPU weight (default 1024)
        nano_cpus: CPU limit as float cores, e.g. 1.5
        cpuset_cpus: CPUs allowed, e.g. "0-2" or "0,1"
    """
    def parse_bytes(s: str) -> int:
        s = s.strip().lower()
        units = {"k": 1024, "m": 1024**2, "g": 1024**3}
        if s[-1] in units:
            return int(float(s[:-1]) * units[s[-1]])
        return int(s)

    c = client().containers.get(container_name)
    kwargs: dict = {}
    if memory      is not None: kwargs["mem_limit"]    = parse_bytes(memory)
    if memory_swap is not None: kwargs["memswap_limit"] = parse_bytes(memory_swap)
    if cpu_shares  is not None: kwargs["cpu_shares"]   = cpu_shares
    if nano_cpus   is not None: kwargs["nano_cpus"]    = int(nano_cpus * 1e9)
    if cpuset_cpus is not None: kwargs["cpuset_cpus"]  = cpuset_cpus

    c.update(**kwargs)
    c.reload()
    return list_resource_limits(container_name)


@mcp.tool()
def exec_container(
    container_name: str,
    command: str,
    workdir: str | None = None,
    environment: dict | None = None,
    user: str | None = None,
) -> dict:
    """
    Execute a command inside a running container.
    If EXEC_WHITELIST env is set, only listed commands are allowed.

    Args:
        container_name: Container name or ID
        command: Shell command string, e.g. "ls -la /app"
        workdir: Working directory inside container
        environment: Extra env vars for this exec
        user: Run as this user, e.g. "root" or "1000"
    """
    allowed = ", ".join(EXEC_WHITELIST) if EXEC_WHITELIST else "ALL (No restrictions)"
    exec_container.__doc__ = f"Execute command in container. ALLOWED COMMANDS: {allowed}"

    command_clean = command.strip()
    cmd_name = command_clean.split()[0]
    
    if EXEC_WHITELIST is not None and cmd_name not in EXEC_WHITELIST:
        return {
            "exit_code": 1,
            "output": f"ERROR: '{cmd_name}' is not in whitelist. Allowed: {allowed}",
        }

    try:
        c = client().containers.get(container_name)
        kwargs: dict = {"cmd": ["/bin/sh", "-c", command_clean], "stdout": True, "stderr": True}
        if workdir:     kwargs["workdir"]     = workdir
        if environment: kwargs["environment"] = environment
        if user:        kwargs["user"]        = user

        exit_code, output = c.exec_run(**kwargs)
        
        decoded_output = output.decode("utf-8", errors="replace")
        if len(decoded_output) > 4000:
            decoded_output = decoded_output[:4000] + "\n... [Output truncated to save tokens] ..."

        return {
            "exit_code": exit_code,
            "output": decoded_output,
        }
    except Exception as e:
        return {"exit_code": 1, "output": str(e)}



# ===========================================================================
# TOOLS - Images
# ===========================================================================

@mcp.tool()
def list_images(name: str | None = None) -> list[dict]:
    """
    List local Docker images.

    Args:
        name: Filter by image name (optional)
    """
    images = client().images.list(name=name)
    result = []
    for img in images:
        result.append({
            "id":      img.short_id,
            "tags":    img.tags,
            "size_mb": round(img.attrs["Size"] / 1024 / 1024, 1),
            "created": img.attrs["Created"][:19].replace("T", " "),
        })
    return result


@mcp.tool()
def pull_image(image: str, tag: str = "latest") -> dict:
    """
    Pull an image from a registry.

    Args:
        image: Image name, e.g. "nginx"
        tag: Tag to pull (default "latest")
    """
    img = client().images.pull(image, tag=tag)
    return {"id": img.short_id, "tags": img.tags}


@mcp.tool()
def push_image(image: str, tag: str = "latest", auth_config: dict | None = None) -> str:
    """
    Push an image to a registry.

    Args:
        image: Image name
        tag: Tag to push (default "latest")
        auth_config: Optional auth dict {"username": ..., "password": ...}
    """
    kwargs: dict = {"tag": tag, "stream": False}
    if auth_config:
        kwargs["auth_config"] = auth_config
    result = client().images.push(image, **kwargs)
    return result


@mcp.tool()
def build_image(
    path: str,
    tag: str | None = None,
    dockerfile: str = "Dockerfile",
    buildargs: dict | None = None,
    rm: bool = True,
) -> dict:
    """
    Build an image from a Dockerfile on the server.

    Args:
        path: Path to build context directory on the server
        tag: Image tag, e.g. "myapp:1.0"
        dockerfile: Dockerfile name (default "Dockerfile")
        buildargs: Build-time variables dict
        rm: Remove intermediate containers (default True)
    """
    kwargs: dict = {"path": path, "dockerfile": dockerfile, "rm": rm}
    if tag:       kwargs["tag"]       = tag
    if buildargs: kwargs["buildargs"] = buildargs

    img, logs = client().images.build(**kwargs)
    log_lines = [l.get("stream", "") for l in logs if "stream" in l]
    return {
        "id":   img.short_id,
        "tags": img.tags,
        "log":  "".join(log_lines)[-2000:],
    }


@mcp.tool()
def remove_image(image: str, force: bool = False, noprune: bool = False) -> dict:
    """
    Remove a local image.

    Args:
        image: Image name or ID
        force: Force removal
        noprune: Don't delete untagged parent images
    """
    client().images.remove(image, force=force, noprune=noprune)
    return {"image": image, "removed": True}


# ===========================================================================
# TOOLS - Networks
# ===========================================================================

@mcp.tool()
def list_networks() -> list[dict]:
    """List all Docker networks."""
    networks = client().networks.list()
    return [
        {
            "id":     n.short_id,
            "name":   n.name,
            "driver": n.attrs["Driver"],
            "scope":  n.attrs["Scope"],
        }
        for n in networks
    ]


@mcp.tool()
def create_network(
    name: str,
    driver: str = "bridge",
    internal: bool = False,
    labels: dict | None = None,
) -> dict:
    """
    Create a Docker network.

    Args:
        name: Network name
        driver: Driver (bridge / overlay / host / none)
        internal: Restrict external access
        labels: Optional labels dict
    """
    kwargs: dict = {"name": name, "driver": driver, "internal": internal}
    if labels: kwargs["labels"] = labels
    n = client().networks.create(**kwargs)
    return {"id": n.short_id, "name": n.name, "driver": n.attrs["Driver"]}


@mcp.tool()
def remove_network(network_name: str) -> dict:
    """
    Remove a Docker network.

    Args:
        network_name: Network name or ID
    """
    n = client().networks.get(network_name)
    n.remove()
    return {"name": network_name, "removed": True}


# ===========================================================================
# TOOLS - Volumes
# ===========================================================================

@mcp.tool()
def list_volumes() -> list[dict]:
    """List all Docker volumes."""
    volumes = client().volumes.list()
    return [
        {
            "name":       v.name,
            "driver":     v.attrs["Driver"],
            "mountpoint": v.attrs["Mountpoint"],
            "created":    v.attrs.get("CreatedAt", "")[:19],
        }
        for v in volumes
    ]


@mcp.tool()
def create_volume(
    name: str,
    driver: str = "local",
    labels: dict | None = None,
    driver_opts: dict | None = None,
) -> dict:
    """
    Create a Docker volume.

    Args:
        name: Volume name
        driver: Volume driver (default "local")
        labels: Optional labels dict
        driver_opts: Driver-specific options
    """
    kwargs: dict = {"name": name, "driver": driver}
    if labels:      kwargs["labels"]      = labels
    if driver_opts: kwargs["driver_opts"] = driver_opts
    v = client().volumes.create(**kwargs)
    return {"name": v.name, "driver": v.attrs["Driver"], "mountpoint": v.attrs["Mountpoint"]}


@mcp.tool()
def remove_volume(volume_name: str, force: bool = False) -> dict:
    """
    Remove a Docker volume.

    Args:
        volume_name: Volume name
        force: Force removal even if in use
    """
    v = client().volumes.get(volume_name)
    v.remove(force=force)
    return {"name": volume_name, "removed": True}


# ===========================================================================
# ASGI app
# ===========================================================================
app = mcp.streamable_http_app()
app.add_middleware(BearerAuthMiddleware)
