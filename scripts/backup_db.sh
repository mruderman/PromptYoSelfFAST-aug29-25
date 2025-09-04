#!/usr/bin/env bash
set -euo pipefail

# Simple backup script for promptyoself.db
# - copies DB to backups/db with a UTC timestamp
# - optionally encrypts with GPG (either recipient or symmetric passphrase)
# - keeps a rotation of recent backups (default KEEP=7)

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DB="$REPO_DIR/promptyoself.db"
BACKUP_DIR="$REPO_DIR/backups/db"
KEEP="${KEEP:-7}"

if [ ! -f "$DB" ]; then
  echo "Error: DB not found at $DB" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
TS=$(date -u +"%Y%m%dT%H%M%SZ")
OUT_BASENAME="promptyoself.$TS.db"
OUT="$BACKUP_DIR/$OUT_BASENAME"

cp -- "$DB" "$OUT"

# Optional encryption: either set GPG_RECIPIENT (public-key) or GPG_SYMM_PASSPHRASE (symmetric)
if [ -n "${GPG_RECIPIENT:-}" ]; then
  gpg --yes --encrypt --recipient "$GPG_RECIPIENT" -o "$OUT.gpg" "$OUT" && rm -f "$OUT"
elif [ -n "${GPG_SYMM_PASSPHRASE:-}" ]; then
  printf "%s" "$GPG_SYMM_PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 --symmetric -o "$OUT.gpg" "$OUT" && rm -f "$OUT"
fi

# Rotation: keep the most recent $KEEP files (both .db and .gpg)
cd "$BACKUP_DIR"
ls -1t | tail -n +$((KEEP+1)) | xargs -r -I{} rm -f -- "{}"

echo "Backup completed: ${OUT##*/}"
