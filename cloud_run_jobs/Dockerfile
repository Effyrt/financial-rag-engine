# Ultra-fast application image (30 seconds build time)
FROM gcr.io/financial-rag-engine/pdf-processor-base:latest

# Copy only application code (changes frequently)
COPY cloud_pipeline.py .
COPY pipeline /app/pipeline

# Create startup script for 10 pages (fast testing)
RUN echo '#!/bin/bash\n\
echo "Starting PDF Processing Job (Ultra-Fast Build)"\n\
echo "Project ID: financial-rag-engine"\n\
echo "Processing: 10 pages for fast testing"\n\
\n\
python cloud_pipeline.py --pages "1-10" --start 1 --end 10 --project-id financial-rag-engine --bucket-name financial-rag-data\n\
\n\
echo "PDF processing job completed!"\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run the startup script
ENTRYPOINT ["/app/start.sh"]
