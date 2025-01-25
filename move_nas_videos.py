#!/usr/bin/env python3
import os
import time
import shutil
import logging
import errno
from logging.handlers import RotatingFileHandler
from datetime import datetime

# ---------------------------------------------------------------------------
# 1. Logging Setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("Mover")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - [Mover] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler with rotation
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"/logs/move_nas_videos_{timestamp}.log"  # Change this to your desired log file path
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ---------------------------------------------------------------------------
# 2. Configuration (via environment variables, or defaults)
# ---------------------------------------------------------------------------
NAS_DIR = os.environ.get("NAS_DIR", "/nas")        # Path where NAS share is mounted (inside container)
LOCAL_DIR = os.environ.get("LOCAL_DIR", "/videos") # Local folder to move files to
MOVE_INTERVAL = int(os.environ.get("MOVE_INTERVAL", "60"))  # How often to poll (seconds)

# ---------------------------------------------------------------------------
# 3. Function to handle cross-device move
# ---------------------------------------------------------------------------
def cross_device_move(source, dest):
    """
    Moves a file even if source and dest are on different devices
    by doing a copy + remove fallback upon EXDEV.
    """
    try:
        shutil.move(source, dest)
    except OSError as e:
        # If the error is EXDEV, it means "Invalid cross-device link" (can't do a simple rename).
        if e.errno == errno.EXDEV:
            logger.info(f"[CrossDevice] Using copy+remove for {source} -> {dest}")
            shutil.copy2(source, dest)
            os.remove(source)
        else:
            raise

# ---------------------------------------------------------------------------
# 4. Logic: Move .MOV files from NAS_DIR to LOCAL_DIR
# ---------------------------------------------------------------------------
def move_new_videos():
    """
    Moves all .MOV files from NAS_DIR to LOCAL_DIR (if they don't already exist).
    Skips hidden files and uses cross_device_move() to handle potential EXDEV errors.
    """
    for entry in os.scandir(NAS_DIR):
        # Skip directories and hidden files
        if entry.is_file() and not entry.name.startswith('.') and entry.name.lower().endswith('.mov'):
            source = os.path.join(NAS_DIR, entry.name)
            dest = os.path.join(LOCAL_DIR, entry.name)

            # Only move if the file doesn't already exist at dest
            if not os.path.exists(dest):
                logger.info(f"Moving {source} -> {dest}")
                try:
                    cross_device_move(source, dest)
                except Exception as err:
                    logger.error(f"Error moving {source}: {err}")
        else:
            if entry.name.startswith('.'):
                logger.info(f"Skipped hidden file: {entry.name}")

def main():
    logger.info(f"Starting poll loop. NAS: {NAS_DIR}, Local: {LOCAL_DIR}, Interval: {MOVE_INTERVAL}s")
    while True:
        move_new_videos()
        time.sleep(MOVE_INTERVAL)

if __name__ == "__main__":
    main()