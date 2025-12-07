# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (ffmpeg needed for moviepy encoding)
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code (this will be mounted as volume in docker-compose)
# But we copy it here for standalone Docker builds
COPY . .

# Create a non-root user for security
RUN useradd -m -u 1000 devuser && \
    chown -R devuser:devuser /app
USER devuser

# Default command (can be overridden)
CMD ["python", "--version"]

