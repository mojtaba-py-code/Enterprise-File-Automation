"""Application service: wire the components together for one batch run."""

from __future__ import annotations

from .config import AppConfig
from .logger import get_logger
from .notifier import EmailNotifier, render_report
from .pipeline import Pipeline, RunReport
from .state import StateStore
from .watcher import InboxWatcher

_log = get_logger("app")


class Application:
    """Owns long-lived components and executes single batch runs.

    Construct once and call :meth:`run_once` repeatedly (e.g. from the
    scheduler); the state store is loaded a single time and reused.
    """

    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg
        self._state = StateStore(cfg.paths.state_file, max_retries=cfg.max_retries)
        self._state.load()
        self._watcher = InboxWatcher(cfg.paths.inbox, self._state, recursive=cfg.recursive)
        self._pipeline = Pipeline(cfg, self._state)
        self._notifier = EmailNotifier(cfg.email)

    def prepare_directories(self) -> None:
        """Create every working directory up front so the first run is clean."""
        for directory in self._cfg.paths.all_dirs():
            directory.mkdir(parents=True, exist_ok=True)

    def run_once(self) -> RunReport:
        """Scan the inbox, process what is pending and report."""
        discovered = self._watcher.scan()
        if not discovered:
            _log.info("nothing to process")
        report = self._pipeline.run(discovered)
        if report.had_activity:
            _log.info(
                "run complete: %d ok, %d failed, %d skipped",
                report.succeeded,
                report.failed,
                report.skipped,
            )
            _log.debug("\n%s", render_report(report))
        self._notifier.notify(report)
        return report
