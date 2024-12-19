import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml  # type: ignore
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Config(BaseModel):
    from_folder_path: Path
    to_folder_path: Path
    trash_path: Path
    ignore_files: List[str]
    ignore_folders: List[str]
    ignore_extensions: List[str]


def load_config(config_path: Optional[Path] = None) -> Dict:
    config_path = config_path or Path(__file__).resolve().parents[2] / "config.yaml"

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found. Expected at {config_path}")

    with open(config_path) as f:
        config_dict = yaml.safe_load(f)

    for key in config_dict:
        if key.endswith("_path"):
            if config_dict[key].startswith("~"):
                config_dict[key] = os.path.expanduser(config_dict[key])
            config_dict[key] = Path(os.path.abspath(config_dict[key]))

    if not os.path.exists(config_dict["trash_path"]):
        raise Exception(f"Could not find Trash folder: '{config["trash_path"]}'")

    config = Config(**config_dict)
    logger.info(f"Config: {config}")

    return config
