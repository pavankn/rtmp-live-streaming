#!/bin/sh
set -e

echo "Starting FastAPI server (on_publish.py)..."
uvicorn on_publish:app --host 0.0.0.0 --port 8081 --reload &

# Wait for background process to keep container alive
wait