import logging
import os
import shutil
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

from backup_assistant.config import Config, load_config
from backup_assistant.logs import configure_logging

logger = logging.getLogger(__name__)


def get_file_paths_with_modified_dates(folder_path: Path) -> Dict[Path, Dict]:
    """Returns dict for files in the given folder:
    {"rel/path/to/file": {"modified_date": modified_date, "abs_path": "abs/path/to/file"}

    "rel/path/to/file" is the relative path w.r.t. the given folder_path
    """
    files_dict = {}
    for root, _, files in os.walk(folder_path):
        for file in files:
            abs_path = Path(os.path.join(root, file))
            modified_date = datetime.fromtimestamp(os.path.getmtime(abs_path))
            rel_path = Path(str(abs_path).replace(f"{folder_path}/", ""))

            files_dict[rel_path] = {"modified_date": modified_date, "abs_path": abs_path}
    return files_dict


class FileClass(Enum):
    IGNORE_FOLDER = "ignore_folder"
    IGNORE_FILE = "ignore_file"
    IGNORE_EXTENSION = "ignore_extension"
    NEW_FILE = "new_file"
    MODIFIED = "modified"
    UNMODIFIED = "unmodified"
    MODIFIED_IN_BACKUP = "modified_in_backup"
    UNKNOWN = "unknown"


def classify_file(
    rel_path: Path,
    from_folder_files: Dict[Path, Dict],
    to_folder_files: Dict[Path, Dict],
    config: Config,
) -> FileClass:
    assert rel_path in from_folder_files, f"{rel_path=} should be in `from_folder_files`"

    for folder_name in config.ignore_folders:
        if f"/{folder_name}/" in str(from_folder_files[rel_path]["abs_path"]):
            return FileClass.IGNORE_FOLDER
    if rel_path.name in config.ignore_files:
        return FileClass.IGNORE_FILE
    elif rel_path.suffix in config.ignore_extensions:
        return FileClass.IGNORE_EXTENSION
    elif rel_path not in to_folder_files:
        return FileClass.NEW_FILE
    elif from_folder_files[rel_path]["modified_date"] > to_folder_files[rel_path]["modified_date"]:
        return FileClass.MODIFIED
    elif from_folder_files[rel_path]["modified_date"] == to_folder_files[rel_path]["modified_date"]:
        return FileClass.UNMODIFIED
    elif from_folder_files[rel_path]["modified_date"] < to_folder_files[rel_path]["modified_date"]:
        return FileClass.MODIFIED_IN_BACKUP
    else:
        return FileClass.UNKNOWN


def log_file_class(rel_path: Path, file_class: FileClass, config: Config) -> None:
    match file_class:
        case (
            FileClass.IGNORE_FOLDER
            | FileClass.IGNORE_FILE
            | FileClass.IGNORE_EXTENSION
            | FileClass.UNMODIFIED
        ):
            logger.debug(f"Ignoring    {f'({file_class.value}):':<19} '{rel_path}'")
        case FileClass.NEW_FILE | FileClass.MODIFIED:
            logger.debug(f"To back up  {f'({file_class.value}):':<19} '{rel_path}'")
        case FileClass.MODIFIED_IN_BACKUP:
            logger.warning(
                f"Modified in backup: '{rel_path}'"
                + f"\n  - FROM path:         '{config.from_folder_path / rel_path}'"
                + f"\n  - TO (backup) path:  '{config.to_folder_path / rel_path}'"
            )
        case FileClass.UNKNOWN:
            logger.warning("UNKNOWN file class. Something is wrong with `classify_file(...)`")
        case _:
            logger.warning("Uncaught file class. Out of sync with `classify_file(...)`")


def get_files_to_backup(
    from_folder_files: Dict[Path, Dict], to_folder_files: Dict[Path, Dict], config: Config
) -> List[Path]:
    backup_files_list = []
    counter = defaultdict(int)  # type: ignore
    for rel_path in from_folder_files:
        file_class = classify_file(rel_path, from_folder_files, to_folder_files, config)
        log_file_class(rel_path, file_class, config)
        counter[file_class] += 1
        if file_class in [FileClass.MODIFIED, FileClass.NEW_FILE]:
            backup_files_list.append(rel_path)
            # TODO: Overwrite back up the files modified in backup folder if frequently happens

    logger.info(
        f"To back up:  {len(backup_files_list):<6}"
        + f"  (new: {counter[FileClass.NEW_FILE]}, modified: {counter[FileClass.MODIFIED]})"
    )

    total_to_ignore = (
        counter[FileClass.IGNORE_FOLDER]
        + counter[FileClass.IGNORE_FILE]
        + counter[FileClass.IGNORE_EXTENSION]
        + counter[FileClass.UNMODIFIED]
    )
    logger.info(
        f"Ignoring:    {total_to_ignore:<6}"
        + f"  (unmodified: {counter[FileClass.UNMODIFIED]}, "
        + f"ignore_file: {counter[FileClass.IGNORE_FILE]}, "
        + f"ignore_folder: {counter[FileClass.IGNORE_FOLDER]}, "
        + f"ignore_extension: {counter[FileClass.IGNORE_EXTENSION]})"
    )
    return backup_files_list


def get_files_to_delete(
    from_folder_files: Dict[Path, Dict],
    to_folder_files: Dict[Path, Dict],
) -> List[Path]:
    """Files in TO folder that are not present (anymore) in the FROM folder"""
    delete_files_list = []
    for rel_path in to_folder_files:
        if rel_path not in from_folder_files:
            delete_files_list.append(rel_path)
    logger.info(f"To delete:   {len(delete_files_list):<7} (exists in TO folder, but not in FROM)")
    return delete_files_list


def get_user_consent(question: str) -> bool:
    """Returns True if user answer to question is yes ("y") and False if no ("n")"""
    user_input = ""
    print()
    while user_input not in ["y", "n"]:
        user_input = input(question + " [y/n]: ").lower()
    print()
    return user_input == "y"


def backup_files(
    backup_files_list: List[Path], config: Config, ask_user_consent: bool = True
) -> None:
    if len(backup_files_list) == 0:
        return

    if ask_user_consent:
        if not get_user_consent("Continue with backup?"):
            logger.info("Quitting")
            exit()

    logger.info("Backing up files")

    for rel_path in tqdm(backup_files_list):
        try:
            from_folder_file_path = config.from_folder_path / rel_path
            to_folder_file_path = config.to_folder_path / rel_path

            os.makedirs(os.path.dirname(to_folder_file_path), exist_ok=True)
            shutil.copy2(from_folder_file_path, to_folder_file_path)

            logger.debug(
                f"Backed up: '{rel_path}'"
                + f"\n  - FROM path:         '{from_folder_file_path}'"
                + f"\n  - TO (backup) path:  '{to_folder_file_path}'"
            )
        except (Exception, KeyboardInterrupt) as e:
            logger.error(
                f"Error occured when backing up: '{rel_path}'"
                + f"\n  - FROM path:         '{from_folder_file_path}'"
                + f"\n  - TO (backup) path:  '{to_folder_file_path}'"
                + f"\n  {type(e).__name__}: {e}"
            )
            raise e


def get_string_list_of_paths(path_list: List[Path], prepend: Optional[Path] = None) -> str:
    """Get string representation of a list of Paths as:
    ...
      - 'path/to/file1.ext'
      - 'path/to/file2.ext'
    ...

    With a prepend (folder) path, a path becomes: '/prepend/path/to/file.ext'
    """
    if prepend is not None:
        prepended_paths = [prepend / file_path for file_path in path_list]
    else:
        prepended_paths = path_list
    list_of_path_strings = [f"'{str(file_path)}'" for file_path in prepended_paths]
    string_list_of_paths = f"\n  - {'\n  - '.join(list_of_path_strings)}"
    return string_list_of_paths


def delete_files(
    delete_files_list: List[Path], config: Config, ask_user_consent: bool = True
) -> None:
    # TODO: delete empty folders after deleting files
    if len(delete_files_list) == 0:
        return

    path_list_str = get_string_list_of_paths(delete_files_list, prepend=config.to_folder_path)
    logger.info(f"Files in TO (backup) folder, not present in FROM folder: {path_list_str}\n")

    if ask_user_consent:
        if not get_user_consent("Delete files?"):
            logger.info("Not deleting files")
            return

    logger.info("Deleting files")

    backup_trash_folder = datetime.now().strftime("backup_trash_%Y-%m-%d_%H;%M;%S")
    for rel_path in tqdm(delete_files_list):
        try:
            to_folder_file_path = config.to_folder_path / rel_path
            trash_file_path = config.trash_path / backup_trash_folder / rel_path

            os.makedirs(os.path.dirname(trash_file_path), exist_ok=True)

            shutil.move(to_folder_file_path, trash_file_path)
            logger.debug(
                f"Moved file to trash: '{rel_path}'"
                + f"\n  - TO (backup) path: '{to_folder_file_path}'"
                + f"\n  - TRASH path:       '{trash_file_path}'"
            )

        except (Exception, KeyboardInterrupt) as e:
            logger.error(f"Error deleting file: '{to_folder_file_path}'\n  {type(e).__name__}: {e}")
            raise e


def run_backup(config_path: Path = "config.yaml"):
    logger.info("Starting up backup assistant 🤖")

    config = load_config(config_path)

    from_folder_files = get_file_paths_with_modified_dates(config.from_folder_path)
    logger.info(f"Files in FROM folder:         {len(from_folder_files)}")

    to_folder_files = get_file_paths_with_modified_dates(config.to_folder_path)
    logger.info(f"Files in TO (backup) folder:  {len(to_folder_files)}")

    backup_files_list = get_files_to_backup(from_folder_files, to_folder_files, config)
    delete_files_list = get_files_to_delete(from_folder_files, to_folder_files)

    backup_files(backup_files_list, config)
    delete_files(delete_files_list, config)

    logger.info("Done 🎉")


if __name__ == "__main__":
    configure_logging()
    run_backup()
