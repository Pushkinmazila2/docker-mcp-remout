# 🚀 Docker MCP Hub - Quick Start

## 📦 What's Included

By default, Docker MCP Hub comes with:
- **HashiCorp Vault** - Secure storage for master encryption keys
- **MCP Hub** - Main application with encrypted data management
- **Automatic setup** - Everything configured out of the box

## ⚡ Quick Start (5 minutes)

### 1. Start the services

```bash
# Clone the repository
git clone <repo-url>
cd docker-mcp-hub

# Start Vault and MCP Hub
docker-compose up -d
```

### 2. Wait for services to be ready

```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f mcp-hub
```

You should see:
```
🔐 VAULT: HASHICORP
   Address: http://vault:8200
✅ Master key loaded from vault
✅ Salt loaded from vault
```

### 3. Get your tokens

Tokens are displayed in the startup logs:

```bash
docker-compose logs mcp-hub | grep TOKEN
```

You'll see:
```
🔑 USER_TOKEN:   <your-user-token>
🔑 ADMIN_TOKEN:  <your-admin-token>
🔑 WEB_UI_TOKEN: <your-webui-token>
```

### 4. Access the Web UI

Open browser: http://localhost:8000

Login with `WEB_UI_TOKEN` or `ADMIN_TOKEN`

### 5. Connect via MCP

**User endpoint:**
```
URL: http://localhost:8000/mcp/user
Token: Bearer <USER_TOKEN>
```

**Admin endpoint:**
```
URL: http://localhost:8000/mcp/admin
Token: Bearer <ADMIN_TOKEN>
```

## 🔐 Security Notes

### Default Configuration (Development)

⚠️ **The default setup uses DEV mode Vault with a static root token!**

This is **NOT secure** for production. It's designed for:
- Local development
- Testing
- Quick demos

### For Production

**Option 1: Secure HashiCorp Vault**

1. Run Vault in production mode (not dev)
2. Initialize and unseal Vault properly
3. Use AppRole or other auth methods
4. Change the root token
5. Enable audit logging

See `VAULT_SETUP.md` for details.

**Option 2: Use Local File Storage**

In `docker_compose.yml`:
```yaml
environment:
  VAULT_TYPE: "local"
```

Then backup `/data` directory regularly.

**Option 3: Use AWS Secrets Manager**

In `docker_compose.yml`:
```yaml
environment:
  VAULT_TYPE: "aws"
  AWS_SECRET_NAME: "docker-mcp-hub/master-keys"
  AWS_REGION: "us-east-1"
```

## 📚 Next Steps

### Add a Remote Server

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-server",
    "host": "192.168.1.100",
    "port": 22,
    "username": "ubuntu",
    "auth_type": "password",
    "password": "your-ssh-password"
  }' \
  http://localhost:8000/api/servers
```

### Create a Custom User Role

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "allowed_tools": ["list_servers", "list_containers", "view_logs"],
    "description": "Read-only developer access"
  }' \
  http://localhost:8000/api/roles
```

### Backup Your Data

```bash
# Encrypted data backup (safe to store anywhere)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/crypto/encrypted-backup > backup.json

# Full backup with master keys (store securely!)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/crypto/full-backup > master-backup.json
```

### Get Help via MCP

Use the `get_help` tool with topics:
- `overview` - System overview
- `backup` - Backup instructions
- `create_user` - User management
- `add_server` - Server management
- `external_vault` - Vault configuration

## 🔧 Troubleshooting

### Vault connection failed

```bash
# Check Vault is running
docker-compose ps vault

# Check Vault logs
docker-compose logs vault

# Test Vault connectivity
curl http://localhost:8200/v1/sys/health
```

### MCP Hub can't connect to Vault

```bash
# Check network
docker network inspect docker-mcp-hub_default

# Verify VAULT_ADDR is correct
docker-compose exec mcp-hub env | grep VAULT

# Try restarting
docker-compose restart mcp-hub
```

### Switch to Local Storage

If Vault is causing issues:

1. Edit `docker_compose.yml`:
   ```yaml
   VAULT_TYPE: "local"
   ```

2. Restart:
   ```bash
   docker-compose restart mcp-hub
   ```

## 📖 Documentation

- `README.md` - Main documentation
- `VAULT_SETUP.md` - Detailed Vault configuration
- `SECURITY_FEATURES.md` - Security architecture
- API docs: http://localhost:8000/docs

## 🆘 Support

For issues, questions, or contributions:
- GitHub Issues: <repo-url>/issues
- Documentation: <repo-url>/wiki

---

**Happy Docker managing! 🐳**
