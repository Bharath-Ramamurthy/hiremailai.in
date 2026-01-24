import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger
import datetime

LOG_DIR = os.getenv("LOG_DIR")

if LOG_DIR is None:
    raise ValueError("LOG_DIR is not set!")

try:
    os.makedirs(LOG_DIR, exist_ok=True)
except PermissionError:
    print(f"Cannot write to log directory: {LOG_DIR}")
    raise


def get_logger(name: str = "GenApply") -> logging.Logger:
    """
    Creates or returns a shared logger with JSON file and console output.
    - Rotates daily at midnight
    - Prevents file lock issues on Windows
    - Avoids duplicate handlers during Streamlit reruns
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers (critical for Streamlit reruns)
    if logger.handlers:
        return logger

    # JSON formatter for structured logs
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    file_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        when="midnight",
        backupCount=14,
        encoding="utf-8",
        delay=True,
        utc=False,
    )

    # --- FIX: safe rename function for Windows ---
    file_handler.namer = (
        lambda name: name
        + "."
        + datetime.datetime.fromtimestamp(file_handler.rolloverAt).strftime("%Y-%m-%d")
    )

    file_handler.rotator = (
        lambda source, dest: os.replace(source, dest)
        if os.path.exists(source)
        else None
    )

    file_handler.setFormatter(formatter)

    # Console handler (colorized or plain for dev)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    # Attach handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
