# 🔐 External Vault Configuration

Docker MCP Hub supports multiple storage backends for master encryption keys:

1. **Local File Storage** (default) - Keys stored in `/data` directory
2. **HashiCorp Vault** - Enterprise-grade secrets management
3. **AWS Secrets Manager** - AWS native secrets storage

## 🏠 Local File Storage (Default)

No configuration needed. Keys are stored in:
- `/data/.master_key` - Master encryption key
- `/data/.salt` - KDF salt

**Pros:**
- Simple, no external dependencies
- Works out of the box

**Cons:**
- Keys stored on disk
- Need to backup `/data` directory
- Single point of failure

---

## 🏢 HashiCorp Vault

### Prerequisites

1. Install hvac library:
```bash
pip install hvac==2.1.0
```

2. Have a running Vault instance

### Configuration

Set environment variables in `docker_compose.yml`:

```yaml
services:
  mcp-hub:
    environment:
      VAULT_TYPE: "hashicorp"
      VAULT_ADDR: "https://vault.example.com:8200"
      VAULT_TOKEN: "your-vault-token"
      VAULT_SECRET_PATH: "secret/data/docker-mcp-hub"  # Optional, default shown
```

### Vault Setup

1. Enable KV v2 secrets engine:
```bash
vault secrets enable -path=secret kv-v2
```

2. Create policy for Docker MCP Hub:
```bash
vault policy write docker-mcp-hub - <<EOF
path "secret/data/docker-mcp-hub" {
  capabilities = ["create", "read", "update", "delete"]
}
EOF
```

3. Create token:
```bash
vault token create -policy=docker-mcp-hub
```

### Using AppRole (Recommended for Production)

```yaml
services:
  mcp-hub:
    environment:
      VAULT_TYPE: "hashicorp"
      VAULT_ADDR: "https://vault.example.com:8200"
      VAULT_ROLE_ID: "your-role-id"
      VAULT_SECRET_ID: "your-secret-id"
```

---

## ☁️ AWS Secrets Manager

### Prerequisites

1. Install boto3:
```bash
pip install boto3==1.34.0
```

2. Have AWS credentials configured

### Configuration

Set environment variables in `docker_compose.yml`:

```yaml
services:
  mcp-hub:
    environment:
      VAULT_TYPE: "aws"
      AWS_SECRET_NAME: "docker-mcp-hub/master-keys"
      AWS_REGION: "us-east-1"
      AWS_ACCESS_KEY_ID: "your-access-key"
      AWS_SECRET_ACCESS_KEY: "your-secret-key"
```

### Using IAM Role (Recommended for EC2/ECS)

```yaml
services:
  mcp-hub:
    environment:
      VAULT_TYPE: "aws"
      AWS_SECRET_NAME: "docker-mcp-hub/master-keys"
      AWS_REGION: "us-east-1"
      # No credentials needed - uses IAM role
```

### AWS Setup

1. Create secret in AWS Secrets Manager:
```bash
aws secretsmanager create-secret \
  --name docker-mcp-hub/master-keys \
  --description "Master encryption keys for Docker MCP Hub" \
  --region us-east-1
```

2. Create IAM policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:CreateSecret",
        "secretsmanager:UpdateSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:docker-mcp-hub/*"
    }
  ]
}
```

3. Attach policy to IAM role or user

---

## 🔄 Migration Between Vault Types

### From Local to External Vault

1. Export current keys:
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/crypto/export > keys-backup.json
```

2. Stop container:
```bash
docker-compose down
```

3. Update `docker_compose.yml` with new vault configuration

4. Start container:
```bash
docker-compose up -d
```

5. Import keys:
```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d @keys-backup.json \
  http://localhost:8000/api/crypto/import
```

### From External Vault to Local

1. Export keys from current vault
2. Set `VAULT_TYPE=local` in docker_compose.yml
3. Restart container
4. Import keys

---

## 🔒 Security Best Practices

### For All Vault Types:

1. **Use TLS/HTTPS** for all vault connections
2. **Rotate tokens/credentials** regularly
3. **Enable audit logging** in your vault
4. **Use least privilege** - only grant necessary permissions
5. **Monitor access** to vault secrets

### For Local Storage:

1. **Encrypt the host filesystem** where `/data` is mounted
2. **Restrict file permissions** (already done: 0600)
3. **Regular backups** of `/data` directory
4. **Store backups encrypted** in separate location

### For HashiCorp Vault:

1. **Use AppRole** instead of tokens in production
2. **Enable auto-unseal** with cloud KMS
3. **Use namespaces** for multi-tenancy
4. **Enable audit device** for compliance

### For AWS Secrets Manager:

1. **Use IAM roles** instead of access keys
2. **Enable automatic rotation** if possible
3. **Use VPC endpoints** for private access
4. **Enable CloudTrail** for audit logs

---

## 🧪 Testing Vault Configuration

After configuring vault, check logs on startup:

```bash
docker-compose logs mcp-hub | grep -i vault
```

You should see:
```
🔐 Using HashiCorp Vault for master keys storage
✅ Master key loaded from vault
✅ Salt loaded from vault
```

Or:
```
🔐 Using AWS Secrets Manager for master keys storage
✅ Master key loaded from vault
✅ Salt loaded from vault
```

---

## ❓ Troubleshooting

### "Failed to connect to vault"

- Check `VAULT_ADDR` is correct and accessible
- Verify network connectivity
- Check firewall rules

### "Authentication failed"

- Verify `VAULT_TOKEN` or AWS credentials are correct
- Check token/credentials have not expired
- Verify IAM permissions (for AWS)

### "Permission denied"

- Check vault policy allows read/write to secret path
- Verify IAM policy (for AWS)

### "Falling back to local storage"

- Vault configuration is set but vault is not accessible
- Check logs for specific error
- Verify required library is installed (hvac or boto3)

---

## 📊 Comparison

| Feature | Local File | HashiCorp Vault | AWS Secrets Manager |
|---------|-----------|-----------------|---------------------|
| Setup Complexity | ⭐ Easy | ⭐⭐⭐ Complex | ⭐⭐ Medium |
| Security | ⭐⭐ Basic | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Very Good |
| Cost | Free | Self-hosted or $$$ | $ Pay per secret |
| Audit Logs | ❌ No | ✅ Yes | ✅ Yes |
| Auto Rotation | ❌ No | ✅ Yes | ✅ Yes |
| HA Support | ❌ No | ✅ Yes | ✅ Yes (built-in) |
| Backup Required | ✅ Manual | ✅ Vault backup | ❌ AWS handles it |

---

## 🎯 Recommendations

- **Development/Testing**: Use Local File Storage
- **Small Production**: Use Local File Storage with encrypted backups
- **Enterprise**: Use HashiCorp Vault or AWS Secrets Manager
- **AWS Infrastructure**: Use AWS Secrets Manager
- **Multi-cloud**: Use HashiCorp Vault
