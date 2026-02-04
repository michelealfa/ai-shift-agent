# Database Setup Guide

This guide explains how to set up and migrate to the PostgreSQL database for the AI Shift Agent.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.9+ with pip
- Existing JSON data files (optional, for migration)

## Quick Start

### 1. Update Environment Variables

Copy `.env.example` to `.env` and update the database settings:

```bash
cp .env.example .env
```

Edit `.env` and set:

```env
DATABASE_URL=postgresql://shift_user:your_secure_password@postgres:5432/shift_agent
DB_PASSWORD=your_secure_password_here
```

### 2. Start PostgreSQL

Start only the PostgreSQL container:

```bash
docker-compose up -d postgres
```

Wait for the database to be ready (check with `docker-compose logs postgres`).

### 3. Install Dependencies

Install the new database dependencies:

```bash
pip install -r requirements.txt
```

Or if using Docker:

```bash
docker-compose build api worker
```

### 4. Migrate Data (Optional)

If you have existing JSON data files, run the migration script:

```bash
python scripts/migrate_json_to_db.py
```

This will:
- Create a backup of your JSON files in `backups/YYYYMMDD_HHMMSS/`
- Migrate users from `config/users.json`
- Migrate settings from `config/dynamic_settings.json`
- Migrate shift backups from `temp/backups/*.json`
- Validate the migration

### 5. Start All Services

Start the complete stack:

```bash
docker-compose up -d
```

### 6. Verify

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "healthy",
  "cache": "healthy"
}
```

## Database Schema

The database includes the following tables:

### Users
- User accounts with authentication
- API keys and personal settings
- Avatar URLs and admin flags

### System Settings
- Global configuration key-value pairs
- Audit trail of who changed what

### Prompts
- AI prompt templates
- Version control for prompts

### Shifts
- User shift data with sync status
- Local cache of Google Sheets data

### Activity Logs
- Audit trail of all system actions
- User ID tracking for debugging

### Sessions
- Web session storage
- Expiration management

## Database Management

### Connect to Database

```bash
# Using Docker
docker exec -it shift_agent_postgres psql -U shift_user -d shift_agent

# Using psql locally
psql postgresql://shift_user:password@localhost:5432/shift_agent
```

### Backup Database

```bash
# Create backup
docker exec shift_agent_postgres pg_dump -U shift_user shift_agent > backup_$(date +%Y%m%d).sql

# Restore backup
docker exec -i shift_agent_postgres psql -U shift_user shift_agent < backup_20260203.sql
```

### View Data

```sql
-- List all users
SELECT id, display_name, is_active FROM users;

-- List all settings
SELECT key, value FROM system_settings;

-- Count shifts by user
SELECT u.display_name, COUNT(s.id) as shift_count
FROM users u
LEFT JOIN shifts s ON u.id = s.user_id
GROUP BY u.id, u.display_name;

-- Recent activity logs
SELECT * FROM recent_activity LIMIT 10;
```

### Reset Database

**⚠️ WARNING: This will delete all data!**

```bash
# Stop containers
docker-compose down

# Remove volume
docker volume rm shift_agent_postgres_data

# Restart
docker-compose up -d postgres
```

## Alembic Migrations (Future)

For schema changes, use Alembic:

```bash
# Initialize Alembic (already done)
alembic init database/migrations

# Create a new migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

## Troubleshooting

### Database Connection Failed

1. Check if PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Check logs:
   ```bash
   docker-compose logs postgres
   ```

3. Verify DATABASE_URL in `.env` matches docker-compose.yml

### Migration Script Errors

1. Ensure PostgreSQL is running and accessible
2. Check that DATABASE_URL is set correctly
3. Verify JSON files exist and are valid
4. Check logs for specific error messages

### Performance Issues

1. Check connection pool settings in `src/database/connection.py`
2. Add indexes for frequently queried columns
3. Monitor slow queries:
   ```sql
   SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
   ```

## Redis Cache

The application uses Redis for:

- **User caching** (5 min TTL)
- **Settings caching** (10 min TTL)
- **API key blacklist** (instant revocation)
- **Rate limiting** (per-user throttling)
- **Session storage**

### Clear Cache

```bash
# Connect to Redis
docker exec -it shift_agent_redis redis-cli

# Clear all cache (database 1)
SELECT 1
FLUSHDB

# View all keys
KEYS *

# Check specific key
GET user:your_api_key_here
```

## Security Best Practices

1. **Change default password**: Update `DB_PASSWORD` in `.env`
2. **Restrict network access**: Don't expose port 5432 in production
3. **Regular backups**: Set up automated pg_dump cron jobs
4. **Monitor logs**: Check `activity_logs` table regularly
5. **Rotate API keys**: Use the admin panel to regenerate keys periodically

## Production Deployment

For production:

1. Use managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
2. Enable SSL connections
3. Set up automated backups
4. Configure connection pooling (pgBouncer)
5. Monitor with pg_stat_statements
6. Set up replication for high availability

## Support

For issues or questions:
1. Check logs: `docker-compose logs api`
2. Verify health endpoint: `curl http://localhost:8000/health`
3. Review database logs: `docker-compose logs postgres`
4. Check migration report in console output
