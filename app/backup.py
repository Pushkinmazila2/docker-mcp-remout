"""
Утилиты для резервного копирования и восстановления криптографических ключей
"""
import os
import base64
import json
from pathlib import Path
from typing import Dict, List
from . import crypto, server_manager

def export_master_keys() -> Dict[str, str]:
    """
    Экспортирует мастер-ключ и соль в base64 формате
    ВАЖНО: Храните эти данные в безопасном месте!
    """
    return {
        "master_key": base64.b64encode(crypto.MASTER_KEY).decode(),
        "salt": base64.b64encode(crypto.SALT).decode(),
        "warning": "KEEP THIS SAFE! Without these keys, encrypted data cannot be recovered!"
    }

def export_encrypted_ssh_keys() -> List[Dict[str, str]]:
    """
    Экспортирует все SSH ключи в зашифрованном виде
    Возвращает список с информацией о ключах и их зашифрованным содержимым
    """
    keys_dir = Path(crypto.KEYS_DIR)
    if not keys_dir.exists():
        return []
    
    exported_keys = []
    
    # Перебираем все файлы в директории ключей
    for key_file in keys_dir.glob('*'):
        if key_file.is_file() and not key_file.name.endswith('.pub'):
            try:
                # Читаем зашифрованное содержимое
                encrypted_content = key_file.read_text()
                
                # Проверяем, есть ли публичный ключ
                pub_key_file = Path(str(key_file) + '.pub')
                pub_key = pub_key_file.read_text() if pub_key_file.exists() else None
                
                exported_keys.append({
                    "filename": key_file.name,
                    "encrypted_private_key": encrypted_content,
                    "public_key": pub_key,
                })
            except Exception as e:
                print(f"Failed to export key {key_file.name}: {e}")
    
    return exported_keys

def export_encrypted_data_backup() -> Dict:
    """
    Экспорт ТОЛЬКО зашифрованных данных (без мастер-ключей):
    - Зашифрованные SSH ключи
    - Конфигурация серверов (с зашифрованными паролями)
    - Роли пользователей (с зашифрованными токенами)
    
    Этот бэкап безопасен для хранения, так как без мастер-ключа данные не расшифровать.
    Доступен для user и admin.
    """
    from datetime import datetime
    
    # Экспортируем SSH ключи
    ssh_keys = export_encrypted_ssh_keys()
    
    # Экспортируем конфигурацию серверов
    servers_file = server_manager.DATA_FILE
    servers_data = None
    if servers_file.exists():
        servers_data = servers_file.read_text()
    
    # Экспортируем роли
    from . import role_manager
    roles_file = role_manager.ROLES_FILE
    roles_data = None
    if roles_file.exists():
        roles_data = roles_file.read_text()
    
    return {
        "backup_version": "1.0",
        "backup_type": "encrypted_data",
        "timestamp": datetime.utcnow().isoformat(),
        "ssh_keys": ssh_keys,
        "servers_config": servers_data,
        "roles_config": roles_data,
        "note": "This backup contains ENCRYPTED data. You need master keys to decrypt it."
    }

def export_full_backup() -> Dict:
    """
    Полный экспорт ВСЕХ данных (только для admin):
    - Мастер-ключ и соль
    - Зашифрованные SSH ключи
    - Конфигурация серверов (с зашифрованными паролями)
    - Роли пользователей (с зашифрованными токенами)
    
    ⚠️ КРИТИЧЕСКИ ВАЖНО: Этот бэкап содержит мастер-ключи!
    """
    from datetime import datetime
    
    # Получаем зашифрованные данные
    encrypted_backup = export_encrypted_data_backup()
    
    # Добавляем мастер-ключи
    master_keys = export_master_keys()
    
    return {
        "backup_version": "1.0",
        "backup_type": "full",
        "timestamp": datetime.utcnow().isoformat(),
        "master_key": master_keys["master_key"],
        "salt": master_keys["salt"],
        "ssh_keys": encrypted_backup["ssh_keys"],
        "servers_config": encrypted_backup["servers_config"],
        "roles_config": encrypted_backup["roles_config"],
        "warning": "⚠️ CRITICAL: This backup contains MASTER KEYS! Keep it EXTREMELY secure!"
    }

def import_master_keys(master_key_b64: str, salt_b64: str) -> bool:
    """
    Импортирует мастер-ключ и соль из base64 формата
    Используется для восстановления после потери данных
    """
    try:
        master_key = base64.b64decode(master_key_b64)
        salt = base64.b64decode(salt_b64)
        
        # Сохраняем ключи
        crypto.MASTER_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(crypto.MASTER_KEY_FILE, "wb") as f:
            f.write(master_key)
        os.chmod(crypto.MASTER_KEY_FILE, 0o600)
        
        with open(crypto.SALT_FILE, "wb") as f:
            f.write(salt)
        os.chmod(crypto.SALT_FILE, 0o600)
        
        # Обновляем глобальные переменные
        crypto.MASTER_KEY = master_key
        crypto.SALT = salt
        
        return True
    except Exception as e:
        print(f"Failed to import keys: {e}")
        return False

def import_encrypted_data_backup(backup_data: Dict) -> bool:
    """
    Импортирует ТОЛЬКО зашифрованные данные (без мастер-ключей):
    - SSH ключи (зашифрованные)
    - Конфигурацию серверов
    - Роли пользователей
    
    Требует, чтобы мастер-ключи уже были установлены.
    Доступен для user и admin.
    """
    try:
        # Восстанавливаем SSH ключи
        keys_dir = Path(crypto.KEYS_DIR)
        keys_dir.mkdir(parents=True, exist_ok=True)
        
        for key_data in backup_data.get("ssh_keys", []):
            key_file = keys_dir / key_data["filename"]
            key_file.write_text(key_data["encrypted_private_key"])
            os.chmod(key_file, 0o600)
            
            # Восстанавливаем публичный ключ если есть
            if key_data.get("public_key"):
                pub_key_file = Path(str(key_file) + ".pub")
                pub_key_file.write_text(key_data["public_key"])
        
        # Восстанавливаем конфигурацию серверов
        if backup_data.get("servers_config"):
            server_manager.DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            server_manager.DATA_FILE.write_text(backup_data["servers_config"])
        
        # Восстанавливаем роли
        if backup_data.get("roles_config"):
            from . import role_manager
            role_manager.ROLES_FILE.parent.mkdir(parents=True, exist_ok=True)
            role_manager.ROLES_FILE.write_text(backup_data["roles_config"])
        
        return True
    except Exception as e:
        print(f"Failed to import encrypted data backup: {e}")
        return False

def import_full_backup(backup_data: Dict) -> bool:
    """
    Импортирует полный бэкап (только для admin):
    - Мастер-ключ и соль
    - SSH ключи (зашифрованные)
    - Конфигурацию серверов
    - Роли пользователей
    """
    try:
        # Сначала импортируем мастер-ключи
        if not import_master_keys(backup_data["master_key"], backup_data["salt"]):
            return False
        
        # Затем импортируем зашифрованные данные
        return import_encrypted_data_backup(backup_data)
        
    except Exception as e:
        print(f"Failed to import full backup: {e}")
        return False

def get_backup_instructions() -> str:
    """
    Возвращает инструкции по резервному копированию
    """
    keys = export_master_keys()
    return f"""
╔══════════════════════════════════════════════════════════════════════════╗
║              DOCKER MCP HUB - BACKUP & RESTORE INSTRUCTIONS              ║
╚══════════════════════════════════════════════════════════════════════════╝

📦 TWO TYPES OF BACKUPS:

1️⃣  ENCRYPTED DATA BACKUP (Safe to store, accessible by user & admin)
   - Contains: SSH keys, server configs, roles (all ENCRYPTED)
   - Cannot be decrypted without master keys
   - Use for regular backups
   
   Export:  GET  /api/crypto/encrypted-backup
   Restore: POST /api/crypto/encrypted-restore

2️⃣  FULL BACKUP (CRITICAL! Admin only)
   - Contains: Master keys + all encrypted data
   - Can decrypt everything
   - Store in EXTREMELY secure location
   
   Export:  GET  /api/crypto/full-backup
   Restore: POST /api/crypto/full-restore

╔══════════════════════════════════════════════════════════════════════════╗
║                    ⚠️  MASTER KEYS (ADMIN ONLY)                          ║
╚══════════════════════════════════════════════════════════════════════════╝

📋 Master Key (base64):
{keys['master_key']}

📋 Salt (base64):
{keys['salt']}

⚠️  WITHOUT THESE KEYS, ALL ENCRYPTED DATA IS PERMANENTLY LOST!

💾 RECOMMENDED BACKUP STRATEGY:

1. Daily/Weekly: Export encrypted data backup
   curl -H "Authorization: Bearer $TOKEN" \\
     http://localhost:8000/api/crypto/encrypted-backup > backup-$(date +%Y%m%d).json

2. Once (after setup): Export full backup with master keys
   curl -H "Authorization: Bearer $ADMIN_TOKEN" \\
     http://localhost:8000/api/crypto/full-backup > MASTER-BACKUP.json
   
   Store MASTER-BACKUP.json in:
   - Password manager (1Password, Bitwarden, etc.)
   - Encrypted USB drive in safe
   - Encrypted cloud storage with 2FA
   - NEVER in the same location as Docker volumes!

3. Test restore periodically to ensure backups work

🔄 RESTORE SCENARIOS:

Scenario A: Lost /data but have master keys
  1. Start fresh container
  2. POST master keys to /api/crypto/import
  3. POST encrypted backup to /api/crypto/encrypted-restore

Scenario B: Complete disaster recovery
  1. Start fresh container
  2. POST full backup to /api/crypto/full-restore
  3. Everything restored!

Scenario C: Migrate to new server
  1. Export full backup from old server
  2. Start container on new server
  3. POST full backup to new server

⚠️  {keys['warning']}
"""