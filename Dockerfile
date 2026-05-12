# Use the official Microsoft Playwright image which comes with system dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set environment variables to prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install only the Chromium browser (saves space)
RUN playwright install chromium

# Copy the rest of the application code
COPY . .

# Create the outputs directory inside the container
RUN mkdir -p outputs

# Expose the port FastAPI runs on
EXPOSE 8000

# We set the PYTHONPATH so Python knows to look inside 'backend' for imports
CMD ["sh", "-c", "PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000"]