"""Functions in this file should be added as script in pyproject.toml"""

from backup_assistant.logs import configure_logging
from backup_assistant.main import main

configure_logging()


def run_backup_assistant():
    main()
