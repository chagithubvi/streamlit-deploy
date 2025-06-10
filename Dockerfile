FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for building and audio support
RUN apt-get update && apt-get install -y --no-install-recommends \
    git  \
    ffmpeg \
    build-essential \
    gcc \
    libc6-dev \
    python3-dev \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    libavdevice-dev \
    libavfilter-dev \
    libopus-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better cache
COPY requirements.txt /app/

# Upgrade pip, setuptools, wheel before installing requirements
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy rest of the app files
COPY . /app

EXPOSE 8501

CMD ["streamlit", "run", "ui_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false"]
