# RAG Service Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
# Docling requires OpenGL and graphics libraries for PDF processing
# Tesseract OCR for document text extraction
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["python", "main.py"]
