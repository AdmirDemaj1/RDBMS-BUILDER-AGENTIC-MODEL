FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml .
COPY readme.md .

# Copy source code
COPY graph/ ./graph/
COPY utils/ ./utils/
COPY main.py .

# Install the package
RUN pip install --no-cache-dir -e .

# Expose the default LangGraph port
EXPOSE 8000

# The langgraph up command will handle the entrypoint

