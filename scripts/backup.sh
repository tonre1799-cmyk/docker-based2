#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🔄 Starting backup for Kerberos ML platform..."

# 1. Backup PostgreSQL
echo "📦 Backing up PostgreSQL..."
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"

# 2. Backup Redis
echo "📦 Backing up Redis..."
docker compose exec redis redis-cli SAVE
docker cp redis:/data/dump.rdb "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"

# 3. Backup Config
echo "📦 Backing up Configuration..."
tar -czf "${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz" .env infrastructure/

echo "✅ Backup complete!"
echo "Files created in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR" | grep "$TIMESTAMP"
