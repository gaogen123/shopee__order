FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend directory
COPY backend /app/backend

# Set PYTHONPATH to include the root so imports work correctly
ENV PYTHONPATH=/app

# Expose port
EXPOSE 9000

# Run the server
CMD ["python", "backend/server.py"]
