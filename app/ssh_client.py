import paramiko
import tempfile
import os
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

from .models import ServerConfig, ServerAuthType, ContainerInfo
from . import crypto


@contextmanager
def ssh_connect(server: ServerConfig, bearer_token: str = None) -> Generator[paramiko.SSHClient, None, None]:
    """Контекстный менеджер для SSH подключения к хосту"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    temp_key_file = None

    connect_kwargs: dict = {
        "hostname": server.host,
        "port": server.port,
        "username": server.username,
        "timeout": 10,
    }

    try:
        if server.auth_type == ServerAuthType.PASSWORD:
            connect_kwargs["password"] = server.password
        elif server.auth_type in (ServerAuthType.KEY_PATH, ServerAuthType.GENERATE_KEY):
            # Читаем зашифрованный ключ
            key_path = Path(server.key_path)
            if key_path.exists():
                encrypted_key = key_path.read_text()
                
                # Расшифровываем ключ
                try:
                    if bearer_token:
                        decrypted_key = crypto.decrypt_with_bearer(encrypted_key, bearer_token)
                    else:
                        decrypted_key = crypto.decrypt_with_master_key(encrypted_key)
                except:
                    # Если не удалось расшифровать, возможно ключ не зашифрован (обратная совместимость)
                    decrypted_key = encrypted_key
                
                # Создаем временный файл с расшифрованным ключом
                temp_key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key')
                temp_key_file.write(decrypted_key)
                temp_key_file.close()
                os.chmod(temp_key_file.name, 0o600)
                
                connect_kwargs["key_filename"] = temp_key_file.name
            else:
                connect_kwargs["key_filename"] = server.key_path

        client.connect(**connect_kwargs)
        yield client
    finally:
        client.close()
        # Удаляем временный файл с ключом
        if temp_key_file and os.path.exists(temp_key_file.name):
            os.unlink(temp_key_file.name)


def _exec(client: paramiko.SSHClient, cmd: str) -> tuple[str, str, int]:
    """Выполняет команду и возвращает (stdout, stderr, exit_code)"""
    _, stdout, stderr = client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    return stdout.read().decode().strip(), stderr.read().decode().strip(), exit_code


# ── Docker operations ────────────────────────────────────────────────────────

def docker_list_containers(server: ServerConfig, all_containers: bool = True, bearer_token: str = None) -> list[ContainerInfo]:
    """Возвращает список контейнеров с хоста"""
    flag = "-a" if all_containers else ""
    cmd = f'docker ps {flag} --format "{{{{.ID}}}}\\t{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}\\t{{{{.State}}}}\\t{{{{.Ports}}}}"'
    with ssh_connect(server, bearer_token) as client:
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


def docker_start_container(server: ServerConfig, container: str, bearer_token: str = None) -> str:
    """Запускает контейнер по имени или ID"""
    with ssh_connect(server, bearer_token) as client:
        out, err, code = _exec(client, f"docker start {container}")
    if code != 0:
        raise RuntimeError(f"docker start failed: {err}")
    return out


def docker_stop_container(server: ServerConfig, container: str, bearer_token: str = None) -> str:
    """Останавливает контейнер по имени или ID"""
    with ssh_connect(server, bearer_token) as client:
        out, err, code = _exec(client, f"docker stop {container}")
    if code != 0:
        raise RuntimeError(f"docker stop failed: {err}")
    return out


def docker_logs(server: ServerConfig, container: str, tail: int = 100, follow: bool = False, bearer_token: str = None) -> str:
    """Получает логи контейнера"""
    tail_flag = f"--tail {tail}" if tail > 0 else ""
    follow_flag = "-f" if follow else ""
    cmd = f"docker logs {tail_flag} {follow_flag} {container}"
    
    with ssh_connect(server, bearer_token) as client:
        out, err, code = _exec(client, cmd)
    
    if code != 0:
        raise RuntimeError(f"docker logs failed: {err}")
    
    # Логи могут быть в stderr (это нормально для docker logs)
    return out + err


def docker_exec_read_file(server: ServerConfig, container: str, file_path: str, max_lines: int = 1000, bearer_token: str = None) -> str:
    """Читает содержимое файла из контейнера"""
    # Используем head для ограничения количества строк
    cmd = f"docker exec {container} head -n {max_lines} {file_path}"
    
    with ssh_connect(server, bearer_token) as client:
        out, err, code = _exec(client, cmd)
    
    if code != 0:
        raise RuntimeError(f"Failed to read file: {err}")
    
    return out


def docker_exec_command(server: ServerConfig, container: str, command: str, bearer_token: str = None) -> str:
    """Выполняет произвольную команду в контейнере"""
    cmd = f"docker exec {container} {command}"
    
    with ssh_connect(server, bearer_token) as client:
        out, err, code = _exec(client, cmd)
    
    if code != 0:
        raise RuntimeError(f"Command failed: {err}")
    
    return out