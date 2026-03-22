FROM python:3.11-slim

# Set build metadata for reproducibility
LABEL maintainer="VaultPitch Engineering"
LABEL description="VaultPitch TEE Enclave - Verifiable AI for Secure Data Rooms"

WORKDIR /app

# Install system dependencies (minimal for TEE)
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY pitch_policy.json .
COPY index.html .

# Create non-root user for security
RUN useradd -m -u 1000 enclave && chown -R enclave:enclave /app
USER enclave

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the enclave
CMD ["python", "main.py"]