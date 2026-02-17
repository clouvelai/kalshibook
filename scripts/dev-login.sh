#!/usr/bin/env bash
# Dev-only: generate a Supabase session and open Chrome logged in.
# Requires SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DEV_USER_EMAIL in .env
set -euo pipefail

# Load .env from project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env file not found at $ENV_FILE" >&2
  exit 1
fi

# Source .env (handles quoted values)
set -a
source "$ENV_FILE"
set +a

# Validate required vars
for var in SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY DEV_USER_EMAIL; do
  if [[ -z "${!var:-}" ]]; then
    echo "Error: $var is not set in .env" >&2
    exit 1
  fi
done

echo "Generating magic link for $DEV_USER_EMAIL..."

# Step 1: Generate magic link via admin API
GENERATE_RESPONSE=$(curl -s -w "\n%{http_code}" \
  "${SUPABASE_URL}/auth/v1/admin/generate_link" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"magiclink\",\"email\":\"${DEV_USER_EMAIL}\"}")

HTTP_CODE=$(echo "$GENERATE_RESPONSE" | tail -1)
BODY=$(echo "$GENERATE_RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "Error: generate_link failed (HTTP $HTTP_CODE)" >&2
  echo "$BODY" >&2
  exit 1
fi

HASHED_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['hashed_token'])")

if [[ -z "$HASHED_TOKEN" ]]; then
  echo "Error: no hashed_token in response" >&2
  exit 1
fi

echo "Verifying token..."

# Step 2: Verify token to get access_token + refresh_token
VERIFY_RESPONSE=$(curl -s -w "\n%{http_code}" \
  "${SUPABASE_URL}/auth/v1/verify" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"token_hash\":\"${HASHED_TOKEN}\",\"type\":\"magiclink\"}")

HTTP_CODE=$(echo "$VERIFY_RESPONSE" | tail -1)
BODY=$(echo "$VERIFY_RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "Error: verify failed (HTTP $HTTP_CODE)" >&2
  echo "$BODY" >&2
  exit 1
fi

ACCESS_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
REFRESH_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['refresh_token'])")

if [[ -z "$ACCESS_TOKEN" || -z "$REFRESH_TOKEN" ]]; then
  echo "Error: missing tokens in verify response" >&2
  exit 1
fi

# Step 3: Open Chrome with dev-session route
URL="http://localhost:3000/auth/dev-session?access_token=${ACCESS_TOKEN}&refresh_token=${REFRESH_TOKEN}"

echo "Opening Chrome with authenticated session..."
open -a "Google Chrome" "$URL"
echo "Done! You should be logged into the dashboard."
