# Usa l'immagine slim per la base Debian
FROM python:3.12-slim

# Definisce le variabili di ambiente interne per lo script
ENV HLS_PORT=8090
WORKDIR /app

# 1. Installazione FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2. Copia e rende eseguibile lo script di avvio
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Espone la porta INTERNA 8090
EXPOSE 8090

# CMD avvia lo script di gestione
CMD ["/app/entrypoint.sh"]