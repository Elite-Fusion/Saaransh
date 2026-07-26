# Saaransh AI — Backup & Recovery Guide

This document describes how to back up and restore the Saaransh AI system.

---

## Table of Contents

1. [Database Backup](#database-backup)
2. [Database Restore](#database-restore)
3. [Environment Recovery](#environment-recovery)
4. [Disaster Recovery](#disaster-recovery)
5. [Automated Backups](#automated-backups)

---

## Database Backup

### Supabase (Production)

If using Supabase, backups are handled automatically:
- **Daily backups**: Supabase provides automatic daily backups for Pro plans
- **Point-in-time recovery**: Available on Pro plans
- **Manual backup**: Use the Supabase dashboard → Database → Backups

### Manual PostgreSQL Backup

```bash
# Full database backup
pg_dump -h db.your-project.supabase.co -U postgres -d saaransh > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
pg_dump -h db.your-project.supabase.co -U postgres -d saaransh | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup specific tables only
pg_dump -h db.your-project.supabase.co -U postgres -d saaransh \
  -t casemaster -t firregmaster -t users > partial_backup.sql
```

### Docker PostgreSQL Backup

```bash
# From docker-compose
docker exec saaransh-postgres pg_dump -U postgres saaransh > backup.sql

# With timestamp
docker exec saaransh-postgres pg_dump -U postgres saaransh | gzip > backup_$(date +%Y%m%d).sql.gz
```

---

## Database Restore

### Restore from Backup

```bash
# Restore full backup
psql -h db.your-project.supabase.co -U postgres -d saaransh < backup.sql

# Restore compressed backup
gunzip -c backup.sql.gz | psql -h db.your-project.supabase.co -U postgres -d saaransh

# Docker restore
cat backup.sql | docker exec -i saaransh-postgres psql -U postgres -d saaransh
```

### Restore Specific Tables

```bash
# Restore only specific tables
pg_restore -h db.your-project.supabase.co -U postgres -d saaransh -t casemaster backup.dump
```

---

## Environment Recovery

### 1. Clone Repository

```bash
git clone https://github.com/your-org/saaransh-ai.git
cd saaransh-ai
```

### 2. Restore Environment Variables

```bash
# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Edit with production values
nano backend/.env
nano frontend/.env
```

### 3. Restore Database

```bash
# Follow Database Restore steps above
```

### 4. Start Services

```bash
# Docker Compose
docker-compose up -d

# Or manually
cd backend && pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000

cd frontend && npm install && npm run build
```

---

## Disaster Recovery

### Recovery Time Objective (RTO)

- **Target**: < 1 hour
- **Strategy**: Docker Compose redeployment

### Recovery Point Objective (RPO)

- **Target**: < 24 hours
- **Strategy**: Daily automated backups

### Recovery Steps

1. **Assess damage**: Determine what components are affected
2. **Provision new infrastructure**: If servers are down
3. **Restore database**: From latest backup
4. **Deploy application**: Using Docker Compose
5. **Verify health**: Check `/api/v1/health` endpoint
6. **Notify users**: Communicate service restoration

---

## Automated Backups

### Supabase (Recommended)

Supabase handles backups automatically for Pro plans. Configure:
- Go to Supabase Dashboard → Project Settings → Backups
- Enable point-in-time recovery
- Set backup retention period

### Custom Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups/saaransh"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Run backup
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

### Cron Job

```bash
# Run backup daily at 2 AM
0 2 * * * /path/to/scripts/backup.sh >> /var/log/saaransh-backup.log 2>&1
```

---

## Backup Verification

Always verify backups are restorable:

```bash
# Test restore to a separate database
createdb saaransh_test
psql -d saaransh_test < backup.sql

# Verify data
psql -d saaransh_test -c "SELECT COUNT(*) FROM casemaster;"
psql -d saaransh_test -c "SELECT COUNT(*) FROM users;"

# Clean up
dropdb saaransh_test
```

---

## Contacts

For backup/restore issues:
- **Database Admin**: [Your DBA contact]
- **DevOps**: [Your DevOps contact]
- **Supabase Support**: support@supabase.com
