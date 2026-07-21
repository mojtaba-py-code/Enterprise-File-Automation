"""Command-line entry point.

Commands
--------
run       Start the batch scheduler (runs forever).
run-once  Execute a single scan/process cycle and exit.
keygen    Print a fresh Fernet encryption key.
init      Create the working directories for a config.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .app import Application
from .config import AppConfig, load_config
from .exceptions import FileAutomationError
from .logger import configure_logging, get_logger
from .notifier import render_report
from .processors.encryptor import EncryptProcessor
from .scheduler import BatchScheduler

_DEFAULT_CONFIG = "config/config.yaml"


def _load_env() -> None:
    """Load a local .env file if python-dotenv is available (optional)."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional at runtime
        return
    load_dotenv()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file-automation",
        description="Config-driven file automation pipeline.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-c",
        "--config",
        default=_DEFAULT_CONFIG,
        help=f"path to the YAML config (default: {_DEFAULT_CONFIG})",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="start the scheduler (runs forever)")
    sub.add_parser("run-once", help="run a single scan/process cycle")
    sub.add_parser("keygen", help="generate a new Fernet encryption key")
    sub.add_parser("init", help="create working directories for the config")
    return parser


def _load(config_path: str) -> AppConfig:
    cfg = load_config(config_path)
    configure_logging(cfg.logging)
    return cfg


def _cmd_run(config_path: str) -> int:
    cfg = _load(config_path)
    app = Application(cfg)
    scheduler = BatchScheduler(app, cfg.schedule)
    scheduler.run_forever()
    return 0


def _cmd_run_once(config_path: str) -> int:
    cfg = _load(config_path)
    app = Application(cfg)
    app.prepare_directories()
    report = app.run_once()
    print(render_report(report))
    return 0 if report.failed == 0 else 1


def _cmd_init(config_path: str) -> int:
    cfg = _load(config_path)
    app = Application(cfg)
    app.prepare_directories()
    get_logger("main").info("initialized directories for %s", config_path)
    print("Created working directories:")
    for directory in cfg.paths.all_dirs():
        print(f"  {directory}")
    return 0


def _cmd_keygen() -> int:
    print(EncryptProcessor.generate_key())
    return 0


def main(argv: list[str] | None = None) -> int:
    _load_env()
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "keygen":
            return _cmd_keygen()
        if args.command == "init":
            return _cmd_init(args.config)
        if args.command == "run-once":
            return _cmd_run_once(args.config)
        if args.command == "run":
            return _cmd_run(args.config)
    except FileAutomationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.error(f"unknown command: {args.command}")  # pragma: no cover
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
