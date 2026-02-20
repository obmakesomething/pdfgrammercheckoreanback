FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Ensure TLS root certificates are available/up-to-date for upstream HTTPS/gRPC APIs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/ ./backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Set environment variables
ENV PORT=5000
ENV PYTHONUNBUFFERED=1
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV GRPC_DEFAULT_SSL_ROOTS_FILE_PATH=/etc/ssl/certs/ca-certificates.crt

# Change to backend directory
WORKDIR /app/backend

# Expose port
EXPOSE 5000

# Start command
CMD ["python", "app.py"]
