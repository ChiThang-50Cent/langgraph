FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU version

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install torch --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN mkdir /root/.cache \
    && mkdir /root/.cache/huggingface \
    && cp -r /app/hf_cache/* /root/.cache/huggingface \
    && rm -rf /app/hf_cache

# Command to run the application
CMD ["python", "app.py"]