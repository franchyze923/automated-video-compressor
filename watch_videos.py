import os
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ----------------------------
# 1) Configuration via ENV
# ----------------------------
SOURCE_FOLDER = os.environ.get("SOURCE_FOLDER", "/videos")
DEST_FOLDER = os.environ.get("DEST_FOLDER", "/compressed")
HANDBRAKE_CLI = os.environ.get("HANDBRAKE_CLI", "HandBrakeCLI")
PRESET = os.environ.get("HANDBRAKE_PRESET", "Fast 1080p30")

ext_string = os.environ.get("ALLOWED_EXTENSIONS", ".mov,.mp4")
ALLOWED_EXTENSIONS = {ext.strip().lower() for ext in ext_string.split(",")}

CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "2"))   # seconds
MAX_WAIT_TIME  = int(os.environ.get("MAX_WAIT_TIME", "60"))   # seconds

# ----------------------------
# 2) Logging Setup
# ----------------------------
logger = logging.getLogger("Compressor")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - [Compressor] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler with rotation
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"/logs/watch_videos_{timestamp}.log"  # Change this to your desired log file path
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def wait_until_fully_written(file_path):
    logger.info(f"Waiting for file to finish writing: {file_path}")
    start_time = time.time()
    last_size = -1

    while True:
        current_size = os.path.getsize(file_path)
        if current_size == last_size:
            logger.info(f"File size stabilized at {current_size} bytes for {file_path}")
            return True
        last_size = current_size

        if (time.time() - start_time) > MAX_WAIT_TIME:
            logger.warning(f"Timed out waiting for file to stabilize: {file_path}")
            return False

        time.sleep(CHECK_INTERVAL)

class VideoCreatedHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        new_file_path = event.src_path
        file_name = os.path.basename(new_file_path)

        # Ignore hidden files (those starting with a dot)
        if file_name.startswith('.'):
            logger.info(f"Ignored hidden file: {new_file_path}")
            return

        _, ext = os.path.splitext(new_file_path)

        if ext.lower() in ALLOWED_EXTENSIONS:
            logger.info(f"New video detected: {new_file_path}")

            # 1) Wait until the file is fully written
            if not wait_until_fully_written(new_file_path):
                logger.error(f"Skipping compression: file never stabilized: {new_file_path}")
                return

            base_name = os.path.splitext(file_name)[0]
            out_file = os.path.join(DEST_FOLDER, base_name + "_compressed.mp4")

            logger.info(f"Compressing: {new_file_path} -> {out_file}")
            cmd = [
                HANDBRAKE_CLI,
                "-i", new_file_path,
                "-o", out_file,
                "--preset", PRESET
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Compression succeeded for {new_file_path}")
                    # -------------------------------------------
                    # Remove the original .MOV after compression:
                    # -------------------------------------------
                    try:
                        os.remove(new_file_path)
                        logger.info(f"Removed original file: {new_file_path}")
                    except Exception as e:
                        logger.error(f"Error removing original file {new_file_path}: {e}")
                else:
                    logger.error(f"Compression failed for {new_file_path}")
                    logger.error(f"HandBrakeCLI stderr: {result.stderr.strip()}")
            except FileNotFoundError:
                logger.error("HandBrakeCLI not found. Check the HANDBRAKE_CLI path.")
            except Exception as e:
                logger.error(f"ERROR running HandBrakeCLI for {new_file_path}: {e}")

def main():
    event_handler = VideoCreatedHandler()
    observer = Observer()
    observer.schedule(event_handler, SOURCE_FOLDER, recursive=False)  # or True if you need subdirs
    observer.start()

    logger.info(f"Watching '{SOURCE_FOLDER}' for new video files. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping observer...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()