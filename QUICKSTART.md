# 🚀 Quick Start: Database Migration

This guide will help you get the new PostgreSQL database up and running in **5 minutes**.

## Step 1: Update .env File

Add these lines to your `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://shift_user:SecurePassword123@postgres:5432/shift_agent
DB_PASSWORD=SecurePassword123

# Redis Cache
REDIS_CACHE_DB=1
```

> **Important:** Change `SecurePassword123` to a strong password!

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or rebuild Docker containers:

```bash
docker-compose build
```

## Step 3: Start PostgreSQL

```bash
docker-compose up -d postgres redis
```

Wait for PostgreSQL to be ready (~10 seconds):

```bash
docker-compose logs -f postgres
# Look for: "database system is ready to accept connections"
```

## Step 4: Run Migration (Optional)

If you have existing JSON data:

```bash
python scripts/migrate_json_to_db.py
```

This will:
- ✅ Backup your JSON files to `backups/YYYYMMDD_HHMMSS/`
- ✅ Migrate users, settings, and shifts to PostgreSQL
- ✅ Validate the migration

**Expected output:**
```
🚀 Starting JSON to Database Migration
✅ Database connection established
✅ Database tables ready
📦 Creating backup of JSON files...
🔄 Migrating data...
✅ Migrated 2 users from JSON to database
✅ Migrated 8 settings from JSON to database
✅ Migrated 45 shifts from backup to database
✅ Migration completed successfully!
```

## Step 5: Start All Services

```bash
docker-compose up -d
```

## Step 6: Verify

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "ok",
  "database": "healthy",
  "cache": "healthy"
}
```

## 🎉 Done!

Your application is now running with PostgreSQL + Redis!

---

## What Changed?

### Before (JSON Files)
```
config/
  ├── users.json              ❌ File-based
  └── dynamic_settings.json   ❌ File-based
```

### After (Database)
```
PostgreSQL Database:
  ├── users table             ✅ ACID compliant
  ├── system_settings table   ✅ With audit trail
  ├── shifts table            ✅ Indexed queries
  ├── activity_logs table     ✅ User tracking
  ├── prompts table           ✅ Version control
  └── sessions table          ✅ Web sessions

Redis Cache:
  ├── User cache (5 min)      ✅ Fast lookups
  ├── Settings cache (10 min) ✅ Reduced DB load
  └── API key blacklist       ✅ Instant revocation
```

---

## Next Steps

1. **Test User Authentication**
   - Visit `http://localhost:8000`
   - Select a user from the picker
   - Verify API calls work

2. **Check Admin Panel**
   - Visit `http://localhost:8000/admin`
   - View users, logs, and settings

3. **Monitor Logs**
   ```bash
   docker-compose logs -f api
   ```

4. **Explore Database**
   ```bash
   docker exec -it shift_agent_postgres psql -U shift_user -d shift_agent
   
   # List all users
   SELECT * FROM users;
   
   # View recent activity
   SELECT * FROM recent_activity;
   ```

---

## Troubleshooting

### "Database connection failed"

1. Check if PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Verify DATABASE_URL in `.env` matches docker-compose.yml

3. Check PostgreSQL logs:
   ```bash
   docker-compose logs postgres
   ```

### "Migration script errors"

1. Ensure PostgreSQL is running first
2. Check that JSON files exist and are valid
3. Review error messages in console output

### "Health check shows degraded"

This means either database or cache is unhealthy:

```bash
# Check database
docker exec shift_agent_postgres pg_isready -U shift_user

# Check Redis
docker exec shift_agent_redis redis-cli ping
```

---

## Need Help?

- **Database Setup:** See [`database/README.md`](file:///Users/michelealfano/.gemini/antigravity/scratch/ai-shift-agent/database/README.md)
- **Full Implementation Plan:** See [`implementation_plan.md`](file:///Users/michelealfano/.gemini/antigravity/brain/573dae0b-85d3-4a2b-85c5-36a5009736b0/implementation_plan.md)
- **What Was Built:** See [`walkthrough.md`](file:///Users/michelealfano/.gemini/antigravity/brain/573dae0b-85d3-4a2b-85c5-36a5009736b0/walkthrough.md)
