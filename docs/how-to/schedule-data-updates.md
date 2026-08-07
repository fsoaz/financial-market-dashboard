# How to schedule data updates

Automate `python main.py` so local CSVs stay current without a manual run.

## Prerequisites

- A working install (see [Getting started](../getting-started.md))
- Absolute paths to the repository and the virtualenv Python

## Linux / macOS (cron)

1. Find the absolute paths:

   ```bash
   cd /path/to/financial-market-dashboard
   pwd
   which python   # with venv activated, or use venv/bin/python
   ```

2. Edit the crontab:

   ```bash
   crontab -e
   ```

3. Add a daily job (example: 06:00 local time):

   ```cron
   0 6 * * * cd /path/to/financial-market-dashboard && /path/to/financial-market-dashboard/venv/bin/python main.py >> /path/to/financial-market-dashboard/data/update.log 2>&1
   ```

Replace `/path/to/financial-market-dashboard` with your real path.

**Expected result:** After the scheduled time, `data/update.log` shows a new update summary, and CSV mtimes under `data/raw/` and `data/processed/` are recent.

## Windows (Task Scheduler)

1. Open Task Scheduler and create a Basic Task.
2. Set a daily trigger.
3. Action: **Start a program**.
   - Program: `C:\path\to\financial-market-dashboard\venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\path\to\financial-market-dashboard`
4. Save and run the task once manually to confirm.

## After an automated update

The dashboard caches loaded CSVs in-process for one hour. Click **Refresh Data** in the sidebar (or restart Streamlit) to load the new files.

## Related

- [Add assets](add-assets.md) — Change what gets fetched
- [Troubleshooting](troubleshooting.md) — Empty data and API failures
- [Architecture](../explanation/architecture.md) — Why updates write CSVs instead of hitting APIs from the UI
