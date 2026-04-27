from pathlib import Path

from Dev import logger


def ensure_dirs():
    """
    Ensure that the necessary directories exist.
    """
    for dir in ["cache", "downloads"]:
        Path(dir).mkdir(parents=True, exist_ok=True)
    logger.info("Cache directories updated.")
    
