#!/bin/bash

# Start Celery worker in the background
echo "🚀 Starting Celery worker..."
celery -A src.tasks.worker.celery_app worker --loglevel=info &

# Start the FastAPI application on the Render-provided port
echo "🚀 Starting FastAPI API on port $PORT..."
uvicorn src.main:app --host 0.0.0.0 --port $PORT

# Exit with the status of the web server
exit $?
