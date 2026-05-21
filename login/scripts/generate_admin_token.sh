#!/usr/bin/env bash
set -euo pipefail

BYTES="${1:-32}"
ENV_PATH="${2:-}"

if ! [[ "$BYTES" =~ ^[0-9]+$ ]]; then
  echo "Bytes must be a number." >&2
  exit 1
fi

if [ "$BYTES" -lt 16 ]; then
  echo "Bytes must be at least 16 for a strong token." >&2
  exit 1
fi

if [ -z "$ENV_PATH" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ENV_PATH="$SCRIPT_DIR/../.env"
fi

if command -v openssl >/dev/null 2>&1; then
  token="$(openssl rand -base64 "$BYTES")"
else
  token="$(head -c "$BYTES" /dev/urandom | base64)"
fi

# base64url
token="${token//+/-}"
token="${token//\//_}"
token="${token//=}"

env_dir="$(dirname "$ENV_PATH")"
if [ ! -d "$env_dir" ]; then
  mkdir -p "$env_dir"
fi

if [ -f "$ENV_PATH" ]; then
  if grep -q '^ADMIN_API_TOKEN=' "$ENV_PATH"; then
    awk -v token="$token" '{
      if ($0 ~ /^ADMIN_API_TOKEN=/) {
        print "ADMIN_API_TOKEN=" token
      } else {
        print
      }
    }' "$ENV_PATH" > "${ENV_PATH}.tmp"
    mv "${ENV_PATH}.tmp" "$ENV_PATH"
  else
    printf '\nADMIN_API_TOKEN=%s\n' "$token" >> "$ENV_PATH"
  fi
else
  printf 'ADMIN_API_TOKEN=%s\n' "$token" > "$ENV_PATH"
fi

echo "$token"
