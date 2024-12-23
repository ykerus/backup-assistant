from pathlib import Path
from typing import Dict
from backup_assistant.backup import (
    get_empty_folders,
    get_file_paths_with_modified_dates,
    get_files_to_backup,
    get_files_to_delete,
)
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
        # Path("file_1.txt"),  # unmodified
        Path("file_2.txt"),
        Path("folder_1/file_1_1.txt"),
        # Path("folder_1/file_1_2.mp4"),  # ignore
        Path("folder_1/subfolder_1_1/file_1_1_1.txt"),  # modified
        # Path("folder_1/subfolder_1_1/file_1_1_2.txt"),  # unmodified
        Path("folder_2/file_2_1.txt"),
        Path("folder_2/file_2_2.png"),
        # Path("folder_2/subfolder_1_1/*"),  # ignore
        Path("folder_2/subfolder_2_1/file_2_1_1.txt"),
        Path("folder_2/subfolder_2_1/subsubfolder_2_1_1/file_2_1_1_1.docx"),
        # Path("folder_3/*"),  # ignore
    ]

    in_expected_not_in_backup = set(expected_files) - set(backup_files_list)
    in_backup_not_in_expected = set(backup_files_list) - set(expected_files)

    msg = f"\n\n{in_backup_not_in_expected=}\n\n{in_expected_not_in_backup=}\n"
    assert len(in_backup_not_in_expected) == 0 and len(in_expected_not_in_backup) == 0, msg


def test_get_files_to_delete(
    from_folder_files: Dict[Path, Dict], to_folder_files: Dict[Path, Dict]
):
    delete_files_list = get_files_to_delete(from_folder_files, to_folder_files)
    delete_files_list = [file for file in delete_files_list if file.name != ".DS_Store"]

    expected_files = [
        Path("file_3.txt"),
        Path("folder_1/file_1_3.txt"),
        Path("folder_4/file_4_1.txt"),
        Path("folder_4/file_4_2.mp4"),
        Path("folder_4/subfolder_4_1/file_4_1_1.txt"),
    ]

    in_expected_not_in_deleted = set(expected_files) - set(delete_files_list)
    in_deleted_not_in_expected = set(delete_files_list) - set(expected_files)

    msg = f"\n\n{in_deleted_not_in_expected=}\n\n{in_expected_not_in_deleted=}\n"
    assert len(in_deleted_not_in_expected) == 0 and len(in_expected_not_in_deleted) == 0, msg


def test_get_empty_folders():
    empty_folders = get_empty_folders(
        Path("tests/data/empty_folders"), ignore_gitkeep=True, return_abspath=False
    )

    expected_folders = [
        Path("tests/data/empty_folders/subfolder_1/subsubfolder_1"),
        Path("tests/data/empty_folders/subfolder_2/subsubfolder_3"),
        Path("tests/data/empty_folders/subfolder_3/subsubfolder_4/subsubsubfolder_1"),
        Path("tests/data/empty_folders/subfolder_3/subsubfolder_4"),
        Path("tests/data/empty_folders/subfolder_3/subsubfolder_5"),
        Path("tests/data/empty_folders/subfolder_3"),
        Path("tests/data/empty_folders/subfolder_4"),
    ]

    in_expected_not_in_empty = set(expected_folders) - set(empty_folders)
    in_empty_not_in_expected = set(empty_folders) - set(expected_folders)

    msg = f"\n\n{in_empty_not_in_expected=}\n\n{in_expected_not_in_empty=}\n"
    assert len(in_empty_not_in_expected) == 0 and len(in_expected_not_in_empty) == 0, msg
