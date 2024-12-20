from pathlib import Path
from typing import Dict
from backup_assistant.backup import get_file_paths_with_modified_dates, get_files_to_backup
from backup_assistant.config import Config, load_config

import pytest


@pytest.fixture
def config():
    return load_config(config_path=Path("tests/config.yaml"))


@pytest.fixture
def from_folder_files(config: Config):
    return get_file_paths_with_modified_dates(folder_path=config.from_folder_path)


@pytest.fixture
def to_folder_files(config: Config):
    return get_file_paths_with_modified_dates(folder_path=config.to_folder_path)


def test_get_files_to_backup(
    from_folder_files: Dict[Path, Dict], to_folder_files: Dict[Path, Dict], config: Config
):
    backup_files_list = get_files_to_backup(from_folder_files, to_folder_files, config)

    expected_files = [
        Path("file_1.txt"),
        Path("file_2.txt"),
        Path("folder_1/file_1_1.txt"),
        # Path("folder_1/file_1_2.mp4"),  # ignore
        Path("folder_1/subfolder_1_1/file_1_1_1.txt"),
        Path("folder_1/subfolder_1_1/file_1_1_2.txt"),
        Path("folder_2/file_2_1.txt"),
        Path("folder_2/file_2_2.png"),
        # Path("folder_2/subfolder_1_1/*"),  # ignore
        Path("folder_2/subfolder_2_1/file_2_1_1.txt"),
        Path("folder_2/subfolder_2_1/subsubfolder_2_1_1/file_2_1_1_1.docx"),
        # Path("folder_3/*"),  # ignore
    ]

    in_backup_not_in_expected = set(expected_files) - set(backup_files_list)
    in_expected_not_in_backup = set(backup_files_list) - set(expected_files)

    msg = f"\n\n{in_backup_not_in_expected=}\n\n{in_expected_not_in_backup=}\n"
    assert len(in_backup_not_in_expected) == 0 and len(in_expected_not_in_backup) == 0, msg