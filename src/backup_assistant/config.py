import logging
import os
from pathlib import Path
from typing import Dict, List, Union

import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: Path = None) -> Dict[str, Union[str, Path, List[str]]]:
    config_path = config_path or Path(__file__).resolve().parents[2] / "config.yaml"

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found. Expected at {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    expected_keys = [
        "from_folder_path",
        "to_folder_path",
        "trash_path",
        "ignore_files",
        "ignore_folders",
        "ignore_extensions",
    ]
    for key in expected_keys:
        if key not in config:
            raise KeyError(f"Missing key in provided config file: '{key}'")
        if key.endswith("_path"):
            if config[key].startswith("~"):
                config[key] = os.path.expanduser(config[key])
            config[key] = Path(os.path.abspath(config[key]))

    logger.info(f"Config: {config}")

    return config
