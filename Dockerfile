# 1. Base Image: Use a stable Debian image with Python pre-installed (python:3.11-slim)
# This is usually more stable than building Python from scratch.
FROM python:3.11-slim

# 2. Set environment variables to ensure clean shell behavior
ENV PYTHONUNBUFFERED 1
ENV PATH="/usr/bin:${PATH}" 

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install System Dependencies:
#    a) build-essential: Necessary for compiling certain Python packages (like Cython dependencies)
#    b) ffmpeg: CRITICAL system tool for combining audio files (combine_audio_files function)
#    c) libsndfile1: Often required for audio libraries to handle file I/O safely
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy Python requirements file and install dependencies
#    We install requirements before the rest of the code to leverage Docker's caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the application code
#    This copies app.py, pdf_podcast_converter.py, and start.sh
COPY . .

# 7. Command to run the application using Gunicorn
#    This command is what runs your application when the container starts.
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
