"""
scheduler.py — APScheduler cron wrapper.

Запуск:
  python3 scheduler.py          ← блокирующий режим (daemon)
  python3 scheduler.py --once   ← один прогон прямо сейчас (для тестирования)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from weekly_pipeline import run_weekly, WEEKLY_TOPICS

def run_now():
    """Немедленный прогон — для тестирования."""
    print("Running pipeline immediately (--once mode)...")
    run_weekly(WEEKLY_TOPICS)

if __name__ == "__main__":
    if "--once" in sys.argv:
        run_now()
    else:
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger

            scheduler = BlockingScheduler()

            # Каждый понедельник в 09:00 UTC
            scheduler.add_job(
                run_weekly,
                CronTrigger(day_of_week="mon", hour=9, minute=0),
                id="weekly_research",
                name="Weekly Market Intelligence Run",
                misfire_grace_time=3600
            )

            # Ежедневный краткий run (для демо)
            scheduler.add_job(
                lambda: run_weekly(WEEKLY_TOPICS[:1]),
                CronTrigger(hour=9, minute=0),
                id="daily_quick",
                name="Daily Quick Run (first topic)"
            )

            print("Scheduler started.")
            print("Jobs:")
            for job in scheduler.get_jobs():
                print(f"  - {job.name}: {job.trigger}")
            print("\nPress Ctrl+C to stop.")
            scheduler.start()

        except (KeyboardInterrupt, SystemExit):
            print("\nScheduler stopped.")
