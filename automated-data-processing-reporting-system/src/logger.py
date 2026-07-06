"""
Centralized logging setup for the ETL and reporting pipeline.
Logs to both console and a rotating file under logs/.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger(name: str, logs_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    """
    Return a configured logger that writes to console + a rotating log file.

    Args:
        name: usually __name__ of the calling module.
        logs_dir: directory where log files are stored.
        level: logging level (default INFO).
    """
    os.makedirs(logs_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid attaching duplicate handlers if get_logger is called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, "pipeline.log"),
        maxBytes=2_000_000,
        backupCount=5,
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
