#!/bin/sh
set -e

# Run on_publish.py in background (unbuffered)
#python3 -u /app/on_publish.py &

echo "Starting FastAPI server (on_publish.py)..."
uvicorn on_publish:app --host 0.0.0.0 --port 8081 --reload &

# Run stream_relay.py in foreground (unbuffered)
#python3 -u /data/stream_relay.py

# Wait for background process to keep container alive
wait

#ffmpeg -re -stream_loop -1 -i "/videos/giramelle_reenc.mp4" -c copy -f flv "rtmp://${NGINX_HOST}:1935/bulk_streams/stream"
