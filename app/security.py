import re
from typing import Any, Dict, List, Union

# Паттерны для поиска чувствительных данных
SENSITIVE_PATTERNS = [
    # RSA/SSH ключи
    (r'-----BEGIN (?:RSA |OPENSSH |DSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |OPENSSH |DSA |EC )?PRIVATE KEY-----', '***PRIVATE_KEY_REDACTED***'),
    (r'ssh-rsa [A-Za-z0-9+/=]+', 'ssh-rsa ***PUBLIC_KEY_REDACTED***'),
    (r'ssh-ed25519 [A-Za-z0-9+/=]+', 'ssh-ed25519 ***PUBLIC_KEY_REDACTED***'),
    
    # Токены и API ключи
    (r'(?i)(token|api[_-]?key|secret[_-]?key|access[_-]?key)["\s:=]+([A-Za-z0-9_\-]{20,})', r'\1: ***REDACTED***'),
    (r'Bearer [A-Za-z0-9_\-\.]+', 'Bearer ***REDACTED***'),
    
    # Пароли
    (r'(?i)(password|passwd|pwd)["\s:=]+([^\s,\]}"\']+)', r'\1: ***REDACTED***'),
    
    # AWS ключи
    (r'AKIA[0-9A-Z]{16}', '***AWS_KEY_REDACTED***'),
    
    # JWT токены
    (r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', '***JWT_REDACTED***'),
    
    # Переменные окружения с чувствительными данными
    (r'(?i)(SECRET|PASSWORD|TOKEN|KEY|CREDENTIALS)=([^\s]+)', r'\1=***REDACTED***'),
    
    #Django / Flask Secret Key
    (r'(?i)SECRET_KEY["\s:=]+([^\s,\]}"\']+)', 'SECRET_KEY: ***REDACTED***'),

    #GITHUB
    (r'gh[pous]_[a-zA-Z0-9]{36}', '***GITHUB_TOKEN_REDACTED***'),

    #AI_TOKENS
    # Универсальный шаблон для большинства AI сервисов
    (r'\b(sk-(?:ant|proj|svc)-[a-zA-Z0-9-_]{30,}|sk-[a-zA-Z0-9]{30,})\b', '***AI_TOKEN_REDACTED***'),

    #Connection Strings
    (r'(mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis|amqp(?:s)?)://([^@\s!]+):([^@\s!]+)@', r'\1://***USER***:***PASS***@')

]

def mask_sensitive_data(text: str) -> str:
    """
    Маскирует чувствительные данные в тексте
    """
    if not isinstance(text, str):
        return text
    
    masked = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        masked = re.sub(pattern, replacement, masked)
    
    return masked

def mask_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Рекурсивно маскирует чувствительные данные в словаре
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    sensitive_keys = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 
        'access_key', 'secret_key', 'private_key', 'credentials'
    }
    
    for key, value in data.items():
        # Проверяем ключ на чувствительность
        if any(sk in key.lower() for sk in sensitive_keys):
            if value and isinstance(value, str) and len(value) > 0:
                result[key] = '***REDACTED***'
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = mask_dict(value)
        elif isinstance(value, list):
            result[key] = mask_list(value)
        elif isinstance(value, str):
            result[key] = mask_sensitive_data(value)
        else:
            result[key] = value
    
    return result

def mask_list(data: List[Any]) -> List[Any]:
    """
    Рекурсивно маскирует чувствительные данные в списке
    """
    if not isinstance(data, list):
        return data
    
    result = []
    for item in data:
        if isinstance(item, dict):
            result.append(mask_dict(item))
        elif isinstance(item, list):
            result.append(mask_list(item))
        elif isinstance(item, str):
            result.append(mask_sensitive_data(item))
        else:
            result.append(item)
    
    return result

def sanitize_response(data: Union[Dict, List, str, Any]) -> Union[Dict, List, str, Any]:
    """
    Универсальная функция для санитизации любого типа данных
    """
    if isinstance(data, dict):
        return mask_dict(data)
    elif isinstance(data, list):
        return mask_list(data)
    elif isinstance(data, str):
        return mask_sensitive_data(data)
    else:
        return data