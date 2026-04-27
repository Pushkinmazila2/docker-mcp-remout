import json
import os
import uuid
import subprocess
from pathlib import Path
from typing import Optional

from .models import ServerConfig, AddServerRequest, ServerAuthType

DATA_FILE = Path(os.getenv("DATA_DIR", "/data")) / "servers.json"
KEYS_DIR = Path(os.getenv("KEYS_DIR", "/keys"))


def _load() -> dict[str, ServerConfig]:
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE) as f:
        raw = json.load(f)
    return {k: ServerConfig(**v) for k, v in raw.items()}


def _save(servers: dict[str, ServerConfig]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump({k: v.model_dump() for k, v in servers.items()}, f, indent=2)


def list_servers() -> list[ServerConfig]:
    return list(_load().values())


def get_server(server_id: str) -> Optional[ServerConfig]:
    return _load().get(server_id)


def add_server(req: AddServerRequest) -> ServerConfig:
    servers = _load()
    server_id = str(uuid.uuid4())[:8]

    key_name = None

    if req.auth_type == ServerAuthType.GENERATE_KEY:
        # Генерируем SSH ключ
        key_name = f"key_{server_id}"
        private_key_path = KEYS_DIR / key_name
        KEYS_DIR.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(private_key_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"ssh-keygen failed: {result.stderr}")

        os.chmod(private_key_path, 0o600)

        # Возвращаем публичный ключ в описании — его нужно добавить на целевой хост
        pub_key_path = Path(str(private_key_path) + ".pub")
        pub_key = pub_key_path.read_text().strip()
        description = (req.description or "") + f"\n[PUBLIC KEY - add to authorized_keys on host]:\n{pub_key}"
    else:
        description = req.description

    # Определяем key_path в зависимости от типа аутентификации
    if req.auth_type == ServerAuthType.PASSWORD:
        final_key_path = None
    elif req.auth_type == ServerAuthType.KEY_PATH:
        final_key_path = req.key_path
    elif req.auth_type == ServerAuthType.GENERATE_KEY:
        final_key_path = str(KEYS_DIR / key_name) if key_name else None
    else:
        final_key_path = None

    config = ServerConfig(
        id=server_id,
        name=req.name,
        host=req.host,
        port=req.port,
        username=req.username,
        auth_type=req.auth_type,
        password=req.password if req.auth_type == ServerAuthType.PASSWORD else None,
        key_path=final_key_path,
        generated_key_name=key_name,
        description=description,
        tags=req.tags,
    )

    servers[server_id] = config
    _save(servers)
    return config


def remove_server(server_id: str) -> bool:
    servers = _load()
    if server_id not in servers:
        return False
    cfg = servers.pop(server_id)
    # Удаляем сгенерированные ключи если были
    if cfg.generated_key_name:
        for suffix in ("", ".pub"):
            p = KEYS_DIR / (cfg.generated_key_name + suffix)
            if p.exists():
                p.unlink()
    _save(servers)
    return True