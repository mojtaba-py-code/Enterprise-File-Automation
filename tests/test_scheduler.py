"""Tests for the batch scheduler (driven without real waiting)."""

from __future__ import annotations

from pathlib import Path

from file_automation.app import Application
from file_automation.config import AppConfig
from file_automation.scheduler import BatchScheduler


def test_run_immediately_processes_on_start(config: AppConfig, sample_file: Path) -> None:
    # run_immediately -> the first tick happens before the poll loop.
    object.__setattr__(config.schedule, "run_immediately", True)
    app = Application(config)
    scheduler = BatchScheduler(app, config.schedule)

    cycles = scheduler.run_forever(sleep=lambda _s: None, max_cycles=1)

    assert cycles == 1
    assert list(config.paths.output.iterdir())  # file was processed on startup


def test_loop_runs_requested_cycles(config: AppConfig) -> None:
    object.__setattr__(config.schedule, "run_immediately", False)
    app = Application(config)
    scheduler = BatchScheduler(app, config.schedule)

    calls: list[float] = []
    cycles = scheduler.run_forever(sleep=calls.append, max_cycles=3)

    assert cycles == 3
    assert len(calls) == 3  # one sleep per idle poll


def test_tick_survives_errors(config: AppConfig, monkeypatch: object) -> None:
    object.__setattr__(config.schedule, "run_immediately", True)
    app = Application(config)

    def boom() -> None:
        raise RuntimeError("scan blew up")

    # A failing run must not propagate out of the scheduled tick.
    app.run_once = boom  # type: ignore[method-assign]
    scheduler = BatchScheduler(app, config.schedule)
    cycles = scheduler.run_forever(sleep=lambda _s: None, max_cycles=1)
    assert cycles == 1  # loop completed despite the error
