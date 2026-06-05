# Progress Tracker Migration Instructions

## Problem
When moving progress tracking models from `api` app to `progress_tracker` app, Django auto-generated migrations that try to remove fields with existing database constraints, causing:

```
django.db.utils.OperationalError: (1054, "Unknown column 'guest_user_id' in 'CHECK'")
```

## Solution Steps

### Step 1: Delete Auto-Generated Problematic Migrations
If Django auto-generated any problematic migrations (like `0009_remove_dailytarget_guest_user_and_more`), delete them:

```bash
# On the server, check for auto-generated migrations
ls api/migrations/
# Delete any migrations numbered higher than 0005 that remove progress models
rm api/migrations/0009_*.py  # or whatever the problematic migration is
```

### Step 2: Apply Our Custom Migrations

```bash
# Apply the progress_tracker app migrations first
python manage.py migrate progress_tracker 0001 --fake-initial

# Apply the data migration
python manage.py migrate progress_tracker 0002

# Apply the api cleanup migration
python manage.py migrate api 0006
```

### Step 3: If Constraints Still Cause Issues

If you still get constraint errors, use the management command:

```bash
# Check what would be done (dry run)
python manage.py fix_progress_migration --dry-run

# Actually fix the constraints
python manage.py fix_progress_migration

# Then retry the migration
python manage.py migrate
```

### Step 4: Verify Migration Success

```bash
# Check migration status
python manage.py showmigrations

# Verify the new tables exist
python manage.py dbshell
> SHOW TABLES LIKE '%progress%';
> EXIT;
```

## Alternative Quick Fix (If Above Doesn't Work)

If the above approach still has issues, you can manually handle the database:

```sql
-- Connect to your database and run:

-- Drop all constraints from the old tables
SET foreign_key_checks = 0;

-- Drop the old api progress tables if they exist
DROP TABLE IF EXISTS api_dailytarget;
DROP TABLE IF EXISTS api_dailyprogress;
DROP TABLE IF EXISTS api_weeklyprogress;
DROP TABLE IF EXISTS api_useractivity;
DROP TABLE IF EXISTS api_streak;

SET foreign_key_checks = 1;
```

Then run:
```bash
python manage.py migrate --fake api 0006
python manage.py migrate progress_tracker
python manage.py migrate
```

## Verification

After successful migration, verify that:

1. New progress tracking tables exist with `progress_tracker_` prefix
2. Old `api_` progress tables are gone
3. `/api/progress/` endpoints work correctly
4. Progress tracking functionality works in the admin

## Rollback (If Needed)

If you need to rollback:

```bash
# Rollback progress_tracker migrations
python manage.py migrate progress_tracker zero

# Rollback api migrations to before the removal
python manage.py migrate api 0005
```

Note: This will lose any progress tracking data that was migrated to the new app.
