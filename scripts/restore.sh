#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <timestamp>"
    exit 1
fi

TIMESTAMP=$1
BACKUP_DIR="./backups"

echo "⚠️  WARNING: This will overwrite current data. Are you sure? (y/N)"
read -r confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Restoration cancelled."
    exit 0
fi

echo "🔄 Restoring Kerberos ML platform from backup $TIMESTAMP..."

# 1. Restore PostgreSQL
echo "📦 Restoring PostgreSQL..."
gunzip -c "${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz" | docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"

# 2. Restore Redis
echo "📦 Restoring Redis..."
docker cp "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb" redis:/data/dump.rdb
docker compose restart redis

# 3. Restore Config (optional, be careful)
echo "📦 Restoring Configuration..."
# tar -xzf "${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz"

echo "✅ Restoration complete!"
