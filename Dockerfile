# Start from an official Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (specifically ffmpeg)
# apt-get is the Linux command line package manager
RUN apt-get update && apt-get install -y ffmpeg

# Copy Python requirements file and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the application using Gunicorn
CMD ["gunicorn", "app:app"]
