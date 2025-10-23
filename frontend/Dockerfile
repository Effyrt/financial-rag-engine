# Dockerfile for Streamlit Frontend
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

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV BACKEND_URL=${BACKEND_URL}

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting Streamlit Frontend"\n\
echo "Backend URL: $BACKEND_URL"\n\
\n\
# Start the Streamlit server\n\
streamlit run app.py --server.port 8501 --server.address 0.0.0.0\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 8501

# Run the startup script
CMD ["/app/start.sh"]