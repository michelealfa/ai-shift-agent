#!/bin/bash

# Start Celery worker in the background (Optimized for 512MB RAM)
# --concurrency=1: Avoid multi-process overhead
# --max-tasks-per-child=1: Recycle memory after every task
echo "🚀 Starting Celery worker (Low Memory Mode)..."
celery -A src.tasks.worker.celery_app worker --loglevel=info --concurrency=1 --max-tasks-per-child=1 &

# Start the FastAPI application on the Render-provided port
echo "🚀 Starting FastAPI API on port $PORT..."
uvicorn src.main:app --host 0.0.0.0 --port $PORT

# Exit with the status of the web server
exit $?
