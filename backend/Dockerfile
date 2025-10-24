# Dockerfile for FastAPI Backend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional cloud dependencies
RUN pip install --no-cache-dir \
    google-cloud-storage \
    google-cloud-secret-manager \
    psycopg2-binary

# Copy backend code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV GOOGLE_CLOUD_PROJECT=${PROJECT_ID}

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting FastAPI Backend"\n\
echo "Project ID: $PROJECT_ID"\n\
echo "Bucket: $BUCKET_NAME"\n\
\n\
# Start the FastAPI server\n\
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Run the startup script
CMD ["/app/start.sh"]
