# Use a lightweight Python image
FROM python:3.9-slim

# Install HandBrakeCLI
RUN apt-get update && apt-get install -y handbrake-cli && rm -rf /var/lib/apt/lists/*

# Create an app directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy your scripts into /app
COPY watch_videos.py move_nas_videos.py start.sh /app/

# Make sure start.sh is executable
RUN chmod +x /app/start.sh

# Environment defaults (override these in docker-compose if needed)
ENV NAS_DIR="/nas" \
    LOCAL_DIR="/videos" \
    MOVE_INTERVAL="60" \
    SOURCE_FOLDER="/videos" \
    DEST_FOLDER="/compressed" \
    HANDBRAKE_PRESET="Fast 1080p30" \
    ALLOWED_EXTENSIONS=".mov" \
    CHECK_INTERVAL="2" \
    MAX_WAIT_TIME="60"

# We'll watch /videos for new files, move them to /compressed once compressed
VOLUME ["/nas", "/videos", "/compressed"]

# Start the combined process
ENTRYPOINT ["/app/start.sh"]