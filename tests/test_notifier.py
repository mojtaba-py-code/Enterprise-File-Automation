"""Tests for report rendering and the e-mail notifier (no network)."""

from __future__ import annotations

from pathlib import Path

from file_automation.config import EmailConfig
from file_automation.models import ProcessResult
from file_automation.notifier import EmailNotifier, render_report
from file_automation.pipeline import RunReport


def _report() -> RunReport:
    report = RunReport()
    report.add(
        ProcessResult(
            source_path=Path("in/a.txt"),
            status="success",
            original_hash="h1",
            category="documents",
            output_path=Path("out/a.zip"),
        )
    )
    report.add(
        ProcessResult(
            source_path=Path("in/b.txt"),
            status="failed",
            original_hash="h2",
            error="boom",
        )
    )
    return report


def test_render_contains_counts() -> None:
    text = render_report(_report())
    assert "Processed : 2" in text
    assert "Succeeded : 1" in text
    assert "Failed    : 1" in text
    assert "a.zip" in text
    assert "boom" in text


def test_notifier_disabled_does_not_send() -> None:
    notifier = EmailNotifier(EmailConfig(enabled=False))
    assert notifier.notify(_report()) is False


def test_build_message_headers() -> None:
    cfg = EmailConfig(
        enabled=True,
        smtp_host="smtp.example.com",
        sender="from@example.com",
        recipients=("to@example.com",),
        subject_prefix="[FA]",
    )
    msg = EmailNotifier(cfg).build_message(_report())
    assert msg["From"] == "from@example.com"
    assert msg["To"] == "to@example.com"
    assert msg["Subject"].startswith("[FA]")


def test_only_on_activity_suppresses_empty() -> None:
    cfg = EmailConfig(
        enabled=True,
        smtp_host="smtp.example.com",
        sender="from@example.com",
        recipients=("to@example.com",),
        only_on_activity=True,
    )
    assert EmailNotifier(cfg).notify(RunReport()) is False
