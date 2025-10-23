# Minimal Dockerfile for PDF Processing
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install only essential Python packages
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    requests \
    python-dotenv \
    pypdf \
    openai \
    chromadb \
    tqdm

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/processed
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONPATH=/app

# Install additional dependencies for the pipeline
RUN pip install --no-cache-dir \
    docling \
    docling-core \
    langchain \
    langchain-text-splitters \
    langchain-community \
    google-cloud-storage \
    google-cloud-secret-manager

# Set environment variables
ENV PYTHONPATH=/app
ENV GOOGLE_CLOUD_PROJECT=${PROJECT_ID}

# Create startup script that runs the cloud pipeline
RUN echo '#!/bin/bash\n\
echo "Starting PDF Processing Job"\n\
echo "Project ID: financial-rag-engine"\n\
echo "Arguments: $@"\n\
\n\
# Run the cloud pipeline with required arguments (50 pages)\n\
python cloud_pipeline.py --end 50 --project-id financial-rag-engine --bucket-name financial-rag-data\n\
\n\
echo "PDF processing job completed!"\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run the startup script with arguments
ENTRYPOINT ["/app/start.sh"]
