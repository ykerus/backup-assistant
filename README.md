# Backup assistant 🗂️

Helps you create a backup of your files from one folder to another, with configurable files and
folders to ignore. Assumes your files and subfolders to backup are located in one overarching
folder.

## Setup 💻

1. Make sure you have `uv` installed: see [their GitHub repo](https://github.com/astral-sh/uv?tab=readme-ov-file#installation).
2. Configure the `config.yaml` in this project to your needs. The `from_folder_path` is the folder
from which the backup will be made. The `to_folder_path` is the folder in which the backup is or
will be stored.
3. That's it!

## Running the code 🚀

To run the code, run the following from the root of this project:
```bash
uv run backup
```

In each step of the pipeline, the user is asked for consent `[y/n]` before any actions are taken.

## How it works ⚙️

The code collects all files and folder names, including modified dates from the `from_folder` and
compares it to the `to_folder` (i.e. the backup folder).

If a new file was created, or it was modified since the backup, then it will be backed up. Any file
or folder that is specified to be ignored in the `config.yaml` will not be backed up. It can be
useful, for example, to ignore `.venv` folders, as they take a lot of time to backup.

Any file or folder in the `to_folder` that is not anymore in the `from_folder` will be deleted, but
only after the user gives consent.
