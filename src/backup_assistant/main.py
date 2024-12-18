from collections import defaultdict
from enum import Enum
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal

from tqdm import tqdm

from backup_assistant.config import load_config
from backup_assistant.logs import configure_logging

logger = logging.getLogger(__name__)

CONFIG = load_config()


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
    rel_path: Path, from_folder_files: Dict[Path, Dict], to_folder_files: Dict[Path, Dict]
) -> FileClass:
    assert rel_path in from_folder_files, f"{rel_path=} should be in `from_folder_files`"

    for folder_name in CONFIG["ignore_folders"]:
        if f"/{folder_name}/" in str(from_folder_files[rel_path]["abs_path"]):
            return FileClass.IGNORE_FOLDER
    if rel_path.name in CONFIG["ignore_files"]:
        return FileClass.IGNORE_FILE
    elif rel_path.suffix in CONFIG["ignore_extensions"]:
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


def log_file_class(
    file_class: FileClass,
    rel_path: Path,
    from_folder_files: Dict[Path, Dict],
    to_folder_files: Dict[Path, Dict],
) -> None:
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
                + f"\n  - FROM path:         '{from_folder_files[rel_path]['abs_path']}'"
                + f"\n  - TO (backup) path:  '{to_folder_files[rel_path]['abs_path']}'"
            )
        case FileClass.UNKNOWN:
            logger.warning("UNKNOWN file class. Something is wrong with `classify_file(...)`")
        case _:
            logger.warning("Uncaught file class. Out of sync with `classify_file(...)`")


def get_files_to_backup(
    from_folder_files: Dict[Path, Dict],
    to_folder_files: Dict[Path, Dict],
) -> List[Path]:

    backup_files_list = []
    counter = defaultdict(int)
    for rel_path in from_folder_files:
        file_class = classify_file(rel_path, from_folder_files, to_folder_files)
        log_file_class(file_class, rel_path, from_folder_files, to_folder_files)
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
        + f"ignore file: {counter[FileClass.IGNORE_FILE]}, "
        + f"ignore folder: {counter[FileClass.IGNORE_FOLDER]}, "
        + f"ignore extension: {counter[FileClass.IGNORE_EXTENSION]})"
    )
    return backup_files_list


def get_files_to_delete(
    from_folder_files: Dict[Path, Dict],
    to_folder_files: Dict[Path, Dict],
) -> List[Path]:
    delete_files_list = []
    for rel_path in to_folder_files:
        if rel_path not in from_folder_files:
            delete_files_list.append(to_folder_files[rel_path]["abs_path"])
    logger.info(f"To delete:   {len(delete_files_list)}")
    return delete_files_list


def backup_files(backup_files_list: List[str], ask_user_consent: bool = True) -> None:
    if len(backup_files_list) == 0:
        return

    if ask_user_consent:
        user_input = ""
        print()
        while user_input.lower() not in ["y", "n"]:
            user_input = input("Continue with backup? [y/n]: ")
        print()
        if user_input == "n":
            logger.info("Quitting")
            exit()
    logger.info("Backing up files")

    for file_rel_path in tqdm(backup_files_list):
        try:
            from_folder_file_abs_path = os.path.join(CONFIG["from_folder_path"], file_rel_path)
            to_folder_file_abs_path = os.path.join(CONFIG["to_folder_path"], file_rel_path)

            os.makedirs(os.path.dirname(to_folder_file_abs_path), exist_ok=True)
            shutil.copy2(from_folder_file_abs_path, to_folder_file_abs_path)

            logger.debug(
                f"Backed up: '{file_rel_path}'"
                + f"\n  - FROM path: '{from_folder_file_abs_path}'"
                + f"\n  - TO path:   '{to_folder_file_abs_path}'"
            )
        except (Exception, KeyboardInterrupt) as e:
            logger.error(
                f"Error occured when backing up: '{file_rel_path}'"
                + f"\n  - FROM path: {from_folder_file_abs_path}"
                + f"\n  - TO path:   {to_folder_file_abs_path}"
                + f"\n  {type(e).__name__}: {e}"
            )
            raise


def delete_files(delete_files_list: List[str], ask_user_consent: bool = True) -> None:
    if len(delete_files_list) == 0:
        return

    delete_files_abs_path_list = [
        f"'{os.path.join(CONFIG["to_folder_path"], file_rel_path)}'"
        for file_rel_path in delete_files_list
    ]
    if ask_user_consent:
        logger.info(f"Files to delete: \n  - {'\n  - '.join(delete_files_abs_path_list)}\n")
        user_input = ""
        while user_input.lower() not in ["y", "n"]:
            user_input = input("Delete files? [y/n]: ")
        print()
        if user_input == "n":
            logger.info("Not deleting files")
            return
    logger.info("Deleting files")

    if not os.path.exists(CONFIG["trash_path"]):
        raise Exception(f"Could not find Trash folder: '{CONFIG["trash_path"]}'")

    for file_rel_path in tqdm(delete_files_list):
        try:
            to_folder_file_abs_path = os.path.join(CONFIG["to_folder_path"], file_rel_path)
            trash_file_path = os.path.join(CONFIG["trash_path"], file_rel_path)

            os.makedirs(os.path.dirname(trash_file_path), exist_ok=True)

            shutil.move(to_folder_file_abs_path, trash_file_path)
            logger.debug(
                f"Moved file to trash: '{file_rel_path}'"
                + f"\n  - TO path: '{to_folder_file_abs_path}'"
                + f"\n  - TRASH path: '{trash_file_path}'"
            )

        except (Exception, KeyboardInterrupt) as e:
            logger.error(
                f"Error deleting file: '{to_folder_file_abs_path}'\n  {type(e).__name__}: {e}"
            )
            raise


def main():
    logger.info("Starting up backup assistant 🤖")

    from_folder_files = get_file_paths_with_modified_dates(CONFIG["from_folder_path"])
    logger.info(f"Files in FROM folder:  {len(from_folder_files)}")

    to_folder_files = get_file_paths_with_modified_dates(CONFIG["to_folder_path"])
    logger.info(f"Files in TO folder:    {len(to_folder_files)}")

    backup_files_list = get_files_to_backup(from_folder_files, to_folder_files)
    delete_files_list = get_files_to_delete(from_folder_files, to_folder_files)

    backup_files(backup_files_list)
    delete_files(delete_files_list)

    logger.info("Done 🎉")


if __name__ == "__main__":
    configure_logging()
    main()
