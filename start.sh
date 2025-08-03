#!/bin/bash
echo "Starting application..."
echo "PORT is set to: $PORT"
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Installed packages:"
pip list

# Set default port if not set
if [ -z "$PORT" ]; then
    export PORT=8080
    echo "PORT was not set, defaulting to 8080"
fi

# Start the application with error handling
gunicorn --bind 0.0.0.0:$PORT --log-level debug --timeout 120 --workers 2 app:app 