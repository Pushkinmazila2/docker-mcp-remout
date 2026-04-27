import paramiko
from contextlib import contextmanager
from typing import Generator

from .models import ServerConfig, ServerAuthType, ContainerInfo


@contextmanager
def ssh_connect(server: ServerConfig) -> Generator[paramiko.SSHClient, None, None]:
    """Контекстный менеджер для SSH подключения к хосту"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict = {
        "hostname": server.host,
        "port": server.port,
        "username": server.username,
        "timeout": 10,
    }

    if server.auth_type == ServerAuthType.PASSWORD:
        connect_kwargs["password"] = server.password
    elif server.auth_type in (ServerAuthType.KEY_PATH, ServerAuthType.GENERATE_KEY):
        connect_kwargs["key_filename"] = server.key_path

    try:
        client.connect(**connect_kwargs)
        yield client
    finally:
        client.close()


def _exec(client: paramiko.SSHClient, cmd: str) -> tuple[str, str, int]:
    """Выполняет команду и возвращает (stdout, stderr, exit_code)"""
    _, stdout, stderr = client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    return stdout.read().decode().strip(), stderr.read().decode().strip(), exit_code


# ── Docker operations ────────────────────────────────────────────────────────

def docker_list_containers(server: ServerConfig, all_containers: bool = True) -> list[ContainerInfo]:
    """Возвращает список контейнеров с хоста"""
    flag = "-a" if all_containers else ""
    cmd = f'docker ps {flag} --format "{{{{.ID}}}}\\t{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}\\t{{{{.State}}}}\\t{{{{.Ports}}}}"'
    with ssh_connect(server) as client:
        out, err, code = _exec(client, cmd)

    if code != 0:
        raise RuntimeError(f"docker ps failed: {err}")

    containers = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 6:
            parts += [""] * (6 - len(parts))
        containers.append(ContainerInfo(
            id=parts[0],
            name=parts[1],
            image=parts[2],
            status=parts[3],
            state=parts[4],
            ports=parts[5],
        ))
    return containers


def docker_start_container(server: ServerConfig, container: str) -> str:
    """Запускает контейнер по имени или ID"""
    with ssh_connect(server) as client:
        out, err, code = _exec(client, f"docker start {container}")
    if code != 0:
        raise RuntimeError(f"docker start failed: {err}")
    return out


def docker_stop_container(server: ServerConfig, container: str) -> str:
    """Останавливает контейнер по имени или ID"""
    with ssh_connect(server) as client:
        out, err, code = _exec(client, f"docker stop {container}")
    if code != 0:
        raise RuntimeError(f"docker stop failed: {err}")
    return out