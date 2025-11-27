# ML Trainer Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy generated gRPC code
COPY generated/ ./generated/

# Copy application code
COPY main.py .

# Set Python path for imports
ENV PYTHONPATH=/app

# Expose ports
EXPOSE 50052 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the server
CMD ["python", "main.py"]



