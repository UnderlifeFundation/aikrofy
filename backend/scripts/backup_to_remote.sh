#!/bin/bash

# Configuration (loaded from environment variables)
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-}"
DB_NAME="${MYSQL_DATABASE:-aikrofy}"
LOCAL_HOST="${LOCAL_MYSQL_HOST:-127.0.0.1}"
REMOTE_HOST="${REMOTE_MYSQL_HOST:-}"

if [ -z "$REMOTE_HOST" ] || [ -z "$DB_PASS" ]; then
    echo "ERROR: REMOTE_MYSQL_HOST and MYSQL_PASSWORD environment variables are required."
    exit 1
fi

# Log file
LOG_FILE="/root/pymai/backend/scripts/backup.log"
echo "=== Backup started at $(date) ===" >> "$LOG_FILE"

# Perform dump and restore to remote
# --single-transaction is used for InnoDB tables to avoid locking
# --quick is used to dump large tables
mysqldump -h "$LOCAL_HOST" -u "$DB_USER" -p"$DB_PASS" --single-transaction --quick "$DB_NAME" | mysql -h "$REMOTE_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" 2>> "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "SUCCESS: Local database backed up to remote database successfully." >> "$LOG_FILE"
    echo "=== Backup ended successfully at $(date) ===" >> "$LOG_FILE"
    exit 0
else
    echo "ERROR: Database backup failed. Check details above." >> "$LOG_FILE"
    echo "=== Backup failed at $(date) ===" >> "$LOG_FILE"
    exit 1
fi
