# Vertex AI Native PDF Parser
FROM python:3.11-slim

# Install system dependencies (minimal for Document AI)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (much lighter without Docling)
RUN pip install --no-cache-dir \
    google-cloud-storage \
    google-cloud-documentai \
    google-cloud-aiplatform

# Copy parsing script
COPY parsing/parse_pdf_vertex_ai.py /app/parse_pdf.py

# Set working directory
WORKDIR /app

# Run the parser
ENTRYPOINT ["python", "parse_pdf.py"]
