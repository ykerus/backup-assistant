import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from rich.logging import RichHandler
from tqdm import tqdm

logger = logging.getLogger(__name__)

FROM_FOLDER_PATH = "data/from"
TO_FOLDER_PATH = "data/to"

FROM_FOLDER_ABS_PATH = os.path.abspath(FROM_FOLDER_PATH)
TO_FOLDER_ABS_PATH = os.path.abspath(TO_FOLDER_PATH)

TRASH_PATH = "~/.Trash"
TRASH_ABS_PATH = os.path.expanduser("~/.Trash")

SKIP_FILES = [
    ".DS_Store",
]

SKIP_EXTENSIONS = [
    ".pth",
]

SKIP_FOLDERS = [".venv", ".cache", ".mypy_cache", "folder_1/subfolder_1"]


def get_files_with_dates(folder_path: str) -> Dict[str, datetime]:
    files_dict = {}
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            updated_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_rel_path = file_path.replace(f"{folder_path}/", "")
            files_dict[file_rel_path] = updated_time
    return files_dict


def get_files_to_backup(
    from_folder_files: Dict[str, datetime],
    to_folder_files: Dict[str, datetime],
) -> List[str]:
    backup_new_files_list = []
    backup_modified_files_list = []
    skip_unmodified_files_list = []
    skip_ignore_files_list = []
    skip_ignore_folders_files_list = []
    for file_rel_path in from_folder_files:
        file_name = Path(file_rel_path).name
        suffix = Path(file_rel_path).suffix

        from_folder_file_abs_path = os.path.join(FROM_FOLDER_ABS_PATH, file_rel_path)
        to_folder_file_abs_path = os.path.join(TO_FOLDER_ABS_PATH, file_rel_path)

        skip_folder = False
        for folder_name in SKIP_FOLDERS:
            if f"/{folder_name}/" in from_folder_file_abs_path:
                skip_ignore_folders_files_list.append(file_rel_path)
                logger.debug(f"Skipping (ignore folder): '{file_rel_path}'")
                skip_folder = True
                break
        if skip_folder:
            continue
        if (file_name in SKIP_FILES) or (suffix in SKIP_EXTENSIONS):
            skip_ignore_files_list.append(file_rel_path)
            logger.debug(f"Skipping (ignore file):   '{file_rel_path}'")
        elif file_rel_path not in to_folder_files:
            backup_new_files_list.append(file_rel_path)
            logger.debug(f"To back up (new file):    '{file_rel_path}'")
        elif from_folder_files[file_rel_path] > to_folder_files[file_rel_path]:
            backup_modified_files_list.append(file_rel_path)
            logger.debug(f"To back up (modified):    '{file_rel_path}'")
        elif from_folder_files[file_rel_path] == to_folder_files[file_rel_path]:
            skip_unmodified_files_list.append(file_rel_path)
            logger.debug(f"Skipping (unmodified):    '{file_rel_path}'")
        elif from_folder_files[file_rel_path] < to_folder_files[file_rel_path]:
            logger.warning(
                f"Modified in backup: '{file_rel_path}'"
                + f"\n  - FROM path: '{from_folder_file_abs_path}'"
                + f"\n  - TO path:   '{to_folder_file_abs_path}'"
            )

    backup_files_list = backup_new_files_list + backup_modified_files_list
    skip_files_list = (
        skip_unmodified_files_list + skip_ignore_files_list + skip_ignore_folders_files_list
    )

    logger.info(
        f"To back up:  {len(backup_files_list):<6}"
        + f"  (new: {len(backup_new_files_list)}, modified: {len(backup_modified_files_list)})"
    )
    logger.info(
        f"Skipping:    {len(skip_files_list):<6}"
        + f"  (unmodified: {len(skip_unmodified_files_list)}, "
        + f"ignore files: {len(skip_ignore_files_list)}, "
        + f"ignore folder files: {len(skip_ignore_folders_files_list)})"
    )

    return backup_files_list


def get_files_to_delete(
    from_folder_files: Dict[str, datetime],
    to_folder_files: Dict[str, datetime],
) -> List[str]:
    delete_files_list = []
    for file_rel_path in to_folder_files:
        if file_rel_path not in from_folder_files:
            to_folder_file_abs_path = os.path.join(TO_FOLDER_ABS_PATH, file_rel_path)
            delete_files_list.append(file_rel_path)
            logger.debug(f"To delete:  '{to_folder_file_abs_path}'")

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
            from_folder_file_abs_path = os.path.join(FROM_FOLDER_ABS_PATH, file_rel_path)
            to_folder_file_abs_path = os.path.join(TO_FOLDER_ABS_PATH, file_rel_path)

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
        f"'{os.path.join(TO_FOLDER_ABS_PATH, file_rel_path)}'"
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

    if not os.path.exists(TRASH_ABS_PATH):
        raise Exception(f"Could not find Trash folder: '{TRASH_ABS_PATH}'")

    for file_rel_path in tqdm(delete_files_list):
        try:
            to_folder_file_abs_path = os.path.join(TO_FOLDER_ABS_PATH, file_rel_path)
            trash_file_path = os.path.join(TRASH_ABS_PATH, file_rel_path)

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

    from_folder_files = get_files_with_dates(FROM_FOLDER_ABS_PATH)
    logger.info(f"Files in FROM folder:  {len(from_folder_files)}")
    to_folder_files = get_files_with_dates(TO_FOLDER_ABS_PATH)
    logger.info(f"Files in TO folder:    {len(to_folder_files)}")

    backup_files_list = get_files_to_backup(from_folder_files, to_folder_files)
    delete_files_list = get_files_to_delete(from_folder_files, to_folder_files)

    backup_files(backup_files_list)
    delete_files(delete_files_list)

    logger.info("Done 🎉")


if __name__ == "__main__":
    with open("logfile.log", "w") as file:
        pass  # The file is now clearedwith open('logfile.log', 'w') as file:

    file_handler = logging.FileHandler("logfile.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)-7s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )

    stdout_handler = RichHandler()
    stdout_handler.setLevel(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[stdout_handler, file_handler],
    )
    main()
