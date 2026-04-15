FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir requests beautifulsoup4 flask

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p media

# Expose port
EXPOSE 5000

# Start server
CMD ["python", "server.py"]
