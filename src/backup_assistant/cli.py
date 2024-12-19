"""Functions in this file should be added as script in pyproject.toml"""

from backup_assistant.logs import configure_logging
from backup_assistant.backup import run_backup

configure_logging()


def run_backup_from_cli():
    run_backup()
