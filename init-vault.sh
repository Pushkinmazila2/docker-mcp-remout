#!/bin/bash

# Скрипт инициализации HashiCorp Vault для Docker MCP Hub

set -e

echo "🔐 Initializing HashiCorp Vault for Docker MCP Hub..."

# Ждем пока Vault запустится
echo "⏳ Waiting for Vault to be ready..."
until curl -s http://localhost:8200/v1/sys/health > /dev/null 2>&1; do
  sleep 1
done

echo "✅ Vault is ready!"

# Устанавливаем переменные
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='root-token-change-me'

echo "📦 Enabling KV v2 secrets engine..."
vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV v2 already enabled"

echo "📝 Creating policy for Docker MCP Hub..."
vault policy write docker-mcp-hub - <<EOF
path "secret/data/docker-mcp-hub" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/docker-mcp-hub" {
  capabilities = ["list", "read"]
}
EOF

echo "🔑 Creating token for Docker MCP Hub..."
TOKEN=$(vault token create -policy=docker-mcp-hub -format=json | jq -r '.auth.client_token')

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Vault initialized successfully!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📋 Configuration:"
echo "   VAULT_ADDR: http://localhost:8200"
echo "   VAULT_TOKEN: $TOKEN"
echo ""
echo "⚠️  IMPORTANT: Update docker_compose.yml with this token:"
echo ""
echo "   environment:"
echo "     VAULT_TOKEN: \"$TOKEN\""
echo ""
echo "   Or use root token (DEV ONLY):"
echo "     VAULT_TOKEN: \"root-token-change-me\""
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
