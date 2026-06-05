# Monthly Affairs Scraper

This app scrapes `https://uttoron.academy/MonthlyAffairs`, normalizes the page
into issues and blocks, and stores the cleaned result in the local database.

By default, the scraper only syncs the current month, so a daily cron job just
checks whether Uttoron added new entries to this month.

## Manual Run

```bash
python manage.py scrape_monthly_affairs
```

Sync a specific month manually if needed:

```bash
python manage.py scrape_monthly_affairs --year 2026 --month April
```

Force a full block rebuild even when the source HTML hash is unchanged:

```bash
python manage.py scrape_monthly_affairs --force-rebuild
```

## Cron Example

Run every day at 2:30 AM server time:

```cron
30 2 * * * /path/to/venv/bin/python /path/to/project/backend/manage.py scrape_monthly_affairs >> /path/to/project/backend/monthly_affairs_cron.log 2>&1
```
