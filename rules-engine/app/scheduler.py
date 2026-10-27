"""Run each contract on its own cron schedule (the `schedule` field)."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .runner import current_contracts, run_checks

log = logging.getLogger("dataguard.scheduler")


def _job(dataset: str) -> None:
    try:
        run_checks(dataset=dataset, trigger="schedule")
    except Exception:
        log.exception("scheduled run for %s failed", dataset)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    for name, contract in current_contracts().items():
        if contract.schedule:
            scheduler.add_job(_job, CronTrigger.from_crontab(contract.schedule, timezone="UTC"),
                              args=[name], id=f"contract:{name}", replace_existing=True,
                              max_instances=1, coalesce=True)
            log.info("scheduled %s with '%s'", name, contract.schedule)
    scheduler.start()
    return scheduler
