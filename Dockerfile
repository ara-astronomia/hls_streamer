# Usa l'immagine slim per la base Debian
FROM python:3.12-slim
RUN pip install uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock /app/  
RUN uv sync --locked
COPY . /app/

EXPOSE 9000

CMD ["uv", "run", "python", "ws_streamer.py"]