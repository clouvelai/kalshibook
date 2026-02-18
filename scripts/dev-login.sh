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

echo "Generating dev session for $DEV_USER_EMAIL..."

# Use Python for both API calls in one process to avoid OTP expiry between steps
URL=$(python3 << 'PYEOF'
import requests, os, sys

supabase_url = os.environ['SUPABASE_URL']
service_key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
email = os.environ['DEV_USER_EMAIL']

# Step 1: Generate magic link
r = requests.post(f'{supabase_url}/auth/v1/admin/generate_link',
    headers={
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    },
    json={'type': 'magiclink', 'email': email}
)
if r.status_code != 200:
    print(f'Error: generate_link failed (HTTP {r.status_code}): {r.text}', file=sys.stderr)
    sys.exit(1)

hashed_token = r.json()['hashed_token']

# Step 2: Immediately verify to get session tokens
r2 = requests.post(f'{supabase_url}/auth/v1/verify',
    headers={
        'apikey': service_key,
        'Content-Type': 'application/json'
    },
    json={'token_hash': hashed_token, 'type': 'magiclink'}
)
if r2.status_code != 200:
    print(f'Error: verify failed (HTTP {r2.status_code}): {r2.text}', file=sys.stderr)
    sys.exit(1)

data = r2.json()
at = data['access_token']
rt = data['refresh_token']
print(f'http://localhost:3000/auth/dev-session?access_token={at}&refresh_token={rt}')
PYEOF
)

echo "Opening Chrome with authenticated session..."
open -a "Google Chrome" "$URL"
echo "Done! You should be logged into the dashboard."
