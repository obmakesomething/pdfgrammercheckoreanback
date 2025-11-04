FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy backend files
COPY backend/ ./backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Set environment variables
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# Change to backend directory
WORKDIR /app/backend

# Expose port
EXPOSE 5000

# Start command
CMD ["python", "app.py"]
