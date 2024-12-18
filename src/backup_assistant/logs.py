import logging

from rich.logging import RichHandler


def configure_logging() -> None:
    with open("logfile.log", "w") as file:
        pass  # The file is now cleared

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
