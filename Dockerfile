# Development Dockerfile for FastAPI
FROM python:3.11

WORKDIR /app

# Install system dependencies including PostgreSQL client libraries
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install uvicorn with reload support (if not already in requirements.txt)
RUN pip install --no-cache-dir uvicorn[standard]

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Start server with hot reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]