"""
Утилиты для резервного копирования и восстановления криптографических ключей
"""
import os
import base64
from pathlib import Path
from typing import Dict
from . import crypto

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

def get_backup_instructions() -> str:
    """
    Возвращает инструкции по резервному копированию
    """
    keys = export_master_keys()
    return f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    CRITICAL: BACKUP YOUR ENCRYPTION KEYS                 ║
╚══════════════════════════════════════════════════════════════════════════╝

⚠️  WITHOUT THESE KEYS, ALL ENCRYPTED DATA WILL BE LOST IF CONTAINER IS RECREATED!

📋 Master Key (base64):
{keys['master_key']}

📋 Salt (base64):
{keys['salt']}

💾 BACKUP INSTRUCTIONS:
1. Copy these keys to a secure location (password manager, encrypted file, etc.)
2. Keep them separate from your Docker volumes
3. Never commit them to version control

🔄 TO RESTORE:
Use the /api/crypto/import endpoint with these values if you need to restore.

⚠️  {keys['warning']}
"""