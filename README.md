# 🐳 Docker MCP Server

Профессиональный сервер на базе **Model Context Protocol (FastMCP)** для удаленного управления Docker-инфраструктурой через ИИ-ассистентов (Claude, Cursor, Windsurf, Roo Code).
<img src="docker_mcp.png" width="600">
Этот инструмент превращает вашу нейросеть в полноценного DevOps-инженера, позволяя ей управлять контейнерами, анализировать логи и выполнять команды в реальном времени.

---

## ✨ Основные возможности

- **📦 Контейнеры:** Полный цикл управления (list, create, start, stop, remove, restart).
- **📋 Логи и Статистика:** Чтение логов (`tail`) и мониторинг ресурсов (`stats`) в реальном времени.
- **🛠 Инструментарий:** Управление образами (build, pull, push), сетями и томами (volumes).
- **⚡ Безопасный Exec:** Выполнение команд внутри контейнеров с поддержкой **Whitelist** (белого списка).
- **🛡 Безопасность:** Авторизация через `Bearer Token` и встроенная защита от DNS-rebinding.
- **🌐 Web UI:** Интерактивная страница-инструкция по адресу сервера.

---

## 🚀 Быстрый старт (Docker)

Запустите сервер одной командой на удаленном хосте:

```bash
docker run -d \
  --name mcp-docker-manager \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e MCP_AUTH_TOKEN=ваш_секретный_токен \
  -e SERVER_HOST=ваш_ip_адрес \
  -e SERVER_PORT=8000 \
  -e EXEC_WHITELIST=ls,ps,df,top,npm,python \
  mcp-docker-image
```

---

## ⚙️ Конфигурация (Environment Variables)


| Переменная | Описание | Значение по умолчанию |
| :--- | :--- | :--- |
| `MCP_AUTH_TOKEN` | Bearer токен для защиты подключения. | `""` (обязательно для защиты!) |
| `SERVER_HOST` | Публичный IP или домен вашего сервера. | `your-server` |
| `SERVER_PORT` | Порт приложения. | `8000` |
| `EXEC_WHITELIST` | Список разрешенных команд для `exec` через запятую. | `null` (разрешены все) |

---

## 🔌 Подключение к ИИ-клиентам

### 🧩 Claude Desktop
Добавьте в ваш `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "docker-remote": {
      "type": "http",
      "url": "http://ваш-ip:8000/mcp",
      "headers": {
        "Authorization": "Bearer ваш-токен"
      }
    }
  }
}
```

### 💻 Cursor / Windsurf
В настройках MCP выберите тип **HTTP** (или `streamable-http`) и укажите:
- **URL:** `http://ваш-ip:8000/mcp`
- **Headers:** `{"Authorization": "Bearer ваш-токен"}`

---

## 🛠 Доступные инструменты (Tools)

После подключения нейросеть получит доступ к следующим командам:

- **Containers:** `list_containers`, `create_container`, `run_container`, `recreate_container`, `start_container`, `stop_container`, `remove_container`, `fetch_container_logs`, `get_container_stats`, `exec_container`.
- **Images:** `list_images`, `pull_image`, `push_image`, `build_image`, `remove_image`.
- **Volumes & Networks:** `list_volumes`, `create_volume`, `list_networks`, `create_network`.

---

## 🔒 Безопасность и ограничения

1. **Docker Socket:** Приложение требует монтирования `/var/run/docker.sock`. Убедитесь, что сервер защищен фаерволом.
2. **Exec Whitelist:** Используйте переменную `EXEC_WHITELIST`, чтобы ИИ не мог выполнить потенциально опасные команды (например, `rm -rf /`) внутри ваших контейнеров.
3. **Auth:** Если `MCP_AUTH_TOKEN` не задан, сервер будет доступен без авторизации (не рекомендуется).

---
Создано для эффективного управления инфраструктурой через Model Context Protocol.
