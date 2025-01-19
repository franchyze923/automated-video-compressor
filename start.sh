#!/usr/bin/env bash
set -e

echo "[Entrypoint] Starting move_nas_videos.py in background..."
python move_nas_videos.py &

echo "[Entrypoint] Starting watch_videos.py in foreground..."
exec python watch_videos.py