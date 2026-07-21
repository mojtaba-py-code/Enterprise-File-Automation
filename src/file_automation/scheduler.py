"""Batch scheduler: run the pipeline every N minutes until interrupted."""

from __future__ import annotations

from collections.abc import Callable

import schedule

from .app import Application
from .config import ScheduleConfig
from .logger import get_logger

_log = get_logger("scheduler")


class BatchScheduler:
    """Thin wrapper around the ``schedule`` library.

    ``run_forever`` blocks; the loop delay is injected so tests can drive it
    without real waiting.
    """

    def __init__(self, app: Application, cfg: ScheduleConfig) -> None:
        self._app = app
        self._cfg = cfg
        self._scheduler = schedule.Scheduler()

    def _tick(self) -> None:
        try:
            self._app.run_once()
        except Exception:
            _log.exception("unhandled error during scheduled run")

    def run_forever(
        self,
        *,
        sleep: Callable[[float], None] | None = None,
        max_cycles: int | None = None,
    ) -> int:
        """Start the schedule loop.

        Parameters
        ----------
        sleep:
            Delay function between polls (defaults to ``time.sleep``); injectable
            for tests.
        max_cycles:
            Stop after this many idle polls (tests only); ``None`` runs until
            KeyboardInterrupt.
        """
        if sleep is None:
            import time

            sleep = time.sleep

        self._app.prepare_directories()
        self._scheduler.every(self._cfg.interval_minutes).minutes.do(self._tick)
        _log.info("scheduler started (every %d min)", self._cfg.interval_minutes)

        if self._cfg.run_immediately:
            self._scheduler.run_all()

        cycles = 0
        try:
            while max_cycles is None or cycles < max_cycles:
                self._scheduler.run_pending()
                sleep(1)
                cycles += 1
        except KeyboardInterrupt:  # pragma: no cover - interactive stop
            _log.info("scheduler stopped by user")
        return cycles
