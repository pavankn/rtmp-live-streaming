#!/bin/sh
echo "[INIT] Waiting for Directus to start..."
sleep 10

ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="secret"
STATIC_TOKEN="my-global-token-123"
DIRECTUS_URL="http://localhost:8055"

# Login or create admin
ACCESS_TOKEN=$(curl -s -X POST "$DIRECTUS_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" | jq -r '.data.access_token')

# Create static access token if not exists
if [ "$ACCESS_TOKEN" != "null" ]; then
  echo "[INIT] Creating static token..."
  curl -s -X POST "$DIRECTUS_URL/access-tokens" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"StaticToken\",\"token\":\"$STATIC_TOKEN\"}" > /dev/null
fi
