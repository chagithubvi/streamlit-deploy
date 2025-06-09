# Use an official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install system-level dependencies (for audio, etc.)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    libavdevice-dev \
    libavfilter-dev \
    libopus-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "ui_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0",  "--server.enableCORS=false"]
