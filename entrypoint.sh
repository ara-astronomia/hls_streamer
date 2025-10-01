#!/bin/sh

# Uscita immediata se un comando fallisce
set -e

# Variabili locali
HLS_DIR=/tmp/hls_stream
HLS_PORT=8090
RTSP_URL=${RTSP_URL}
GOP_SIZE=10

# 0. Verifica dell'input
if [ -z "$RTSP_URL" ]; then
    echo "Errore: La variabile RTSP_URL non è stata impostata. Interruzione."
    exit 1
fi

# 1. Prepara la directory HLS
echo "--> Creazione della directory HLS: ${HLS_DIR}"
mkdir -p ${HLS_DIR}
# NON serve cd qui, useremo il percorso assoluto

# 2. Avvia FFmpeg (in background)
echo "--> Avvio FFmpeg per proxyare RTSP in HLS rotante: ${RTSP_URL}"
# Usiamo il percorso assoluto: ${HLS_DIR}/stream.m3u8
# ffmpeg -i "${RTSP_URL}" \
#     -c:v copy \
#     -an \
#     -hls_time 1 \
#     -hls_list_size 10 \
#     -hls_flags delete_segments \
#     -f hls "${HLS_DIR}/stream.m3u8" & # <--- CORREZIONE: Percorso assoluto

ffmpeg -i "${RTSP_URL}" -c:v copy -an -g ${GOP_SIZE} -hls_time 1 -hls_list_size 3 -hls_flags delete_segments -f hls "${HLS_DIR}/stream.m3u8" &

# 3. Avvia il server HTTP Python (in foreground)
# Dobbiamo assicurarci che il server HTTP serva dalla directory HLS.
echo "--> Avvio del server HTTP Python sulla porta ${HLS_PORT} servendo da ${HLS_DIR}"
# Usiamo 'cd' qui per spostare il server nella directory corretta prima dell'exec
cd ${HLS_DIR} 
exec python3 -m http.server ${HLS_PORT}
