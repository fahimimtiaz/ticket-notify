# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files
COPY main_unified.py .
COPY main.py .
COPY main_busbd.py .

# Copy cache files if they exist (won't fail if they don't)
COPY ticket_cache*.json* ./

# Create empty cache files if they don't exist
RUN touch ticket_cache.json ticket_cache_busbd.json

# Set environment variables (these will be overridden by Render)
ENV PYTHONUNBUFFERED=1

# Run the unified monitor
CMD ["python", "main_unified.py"]

