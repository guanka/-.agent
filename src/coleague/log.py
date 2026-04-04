"""日志配置"""

import logging
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: Path | str = "/var/log/coleague.log",
) -> logging.Logger:
    logger = logging.getLogger("coleague")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
