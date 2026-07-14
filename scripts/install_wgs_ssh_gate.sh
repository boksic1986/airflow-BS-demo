#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${WGS_PROJECT_ROOT:-/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS}"
SSH_DIR="$PROJECT_ROOT/shared/ssh"
KEY_PATH="${WGS_SSH_KEY_PATH:-$SSH_DIR/id_ed25519}"
AUTHORIZED_KEYS="${WGS_AUTHORIZED_KEYS:-$HOME/.ssh/authorized_keys}"
KEY_COMMENT="airflow-demo-wgs-gate"

mkdir -p "$SSH_DIR" "$(dirname "$AUTHORIZED_KEYS")"
chmod 0700 "$(dirname "$AUTHORIZED_KEYS")"
if [[ ! -f "$KEY_PATH" ]]; then
  ssh-keygen -q -t ed25519 -N "" -C "$KEY_COMMENT" -f "$KEY_PATH"
fi
chgrp "${WGS_SSH_KEY_GID:-$(id -g)}" "$KEY_PATH"
chmod 0640 "$KEY_PATH"
chmod 0644 "$KEY_PATH.pub"

touch "$AUTHORIZED_KEYS"
chmod 0600 "$AUTHORIZED_KEYS"
cp -p "$AUTHORIZED_KEYS" "$AUTHORIZED_KEYS.t127-backup-$(date +%Y%m%d%H%M%S)"
TEMP_KEYS="$AUTHORIZED_KEYS.t127.$$"
grep -v -F "$KEY_COMMENT" "$AUTHORIZED_KEYS" > "$TEMP_KEYS" || true
PUBLIC_KEY="$(cat "$KEY_PATH.pub")"
printf 'restrict,command="%s/bin/wgs-ssh-gate" %s\n' "$PROJECT_ROOT" "$PUBLIC_KEY" >> "$TEMP_KEYS"
chmod 0600 "$TEMP_KEYS"
mv "$TEMP_KEYS" "$AUTHORIZED_KEYS"

ssh-keyscan -H "${WGS_SSH_HOST:-172.17.106.10}" > "$SSH_DIR/known_hosts.partial"
mv "$SSH_DIR/known_hosts.partial" "$SSH_DIR/known_hosts"
chmod 0644 "$SSH_DIR/known_hosts"

echo "Restricted WGS SSH key installed: $KEY_PATH"
