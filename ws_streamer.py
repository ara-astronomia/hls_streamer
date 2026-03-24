# video_ws_east.py

import asyncio
import logging
import websockets
import os
import sys
from dotenv import load_dotenv

load_dotenv()
# Configurazione Log (opzionale, ma utile)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# ===================================================================
# CONFIGURAZIONE HARD-CODED PER EAST
# ===================================================================
CAMERA_NAME = os.getenv("CAMERA_NAME")
# Assicurati che l'URL sia corretto!
RTSP_URL = os.getenv("CAMERA_URL") # "rtsp://admin:camera_est_ara157@192.168.178.32:554/h264Preview_01_sub"
WS_PORT = os.getenv("CAMERA_WS_PORT") #9000

FFMPEG_INPUT_OPTIONS = [
    '-rtsp_transport', 'tcp',       
    '-probesize', '8192',           # Aumentato per migliore analisi
    '-analyzeduration', '500000',   # 500ms di analisi (non 0)
    '-i', RTSP_URL,                
]

# FFMPEG_OUTPUT_OPTIONS: Usa 640x480 se la camera è 4:3 (o 640x360 se è 16:9)
FFMPEG_OUTPUT_OPTIONS = [
    '-an',                          # Output: Nessun audio
    '-f', 'mpegts',
    '-codec:v', 'mpeg1video', 
    '-tune', 'zerolatency',         # Output: Priorità bassa latenza
    '-s', '480x270', 
    '-b:v', '500k', 
    '-r', '20',                     # Mantieni 25fps (o 30 se la sorgente è 30)
    '-q:v', '3',                    # **CRUCIALE SU PI:** Forza una qualità costante (7 è un buon compromesso). 
                                    # Rende l'encoding meno variabile e più leggero della CPU rispetto al solo bitrate.
    '-'                             # Output: Pipe
]
# ===================================================================

# Variabile di stato per i client (solo per questa camera)
clients = {CAMERA_NAME: set()} 
ffmpeg_proc = None # Riferimento al processo FFMPEG

# Handler semplificato: usa la costante globale CAMERA_NAME
async def ws_handler(websocket, path=None):
    clients[CAMERA_NAME].add(websocket)
    logging.info(f"[WS] Client connesso a {CAMERA_NAME} (tot: {len(clients[CAMERA_NAME])})")
    try:
        await websocket.wait_closed()
    finally:
        clients[CAMERA_NAME].discard(websocket)
        logging.info(f"[WS] Client disconnesso da {CAMERA_NAME} (tot: {len(clients[CAMERA_NAME])})")

# Relay Loop semplificato: usa le costanti globali
async def ffmpeg_relay_loop():
    global ffmpeg_proc
    
    cmd = ['ffmpeg'] + FFMPEG_INPUT_OPTIONS + FFMPEG_OUTPUT_OPTIONS
    logging.info(f"[FFMPEG] Avvio ffmpeg per {CAMERA_NAME}: {' '.join(cmd)}")

    ffmpeg_proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=None
    )
    
    await asyncio.sleep(0.5) # Ritardo asincrono

    while True:
        try:
            # Leggi i chunk
            chunk = await asyncio.wait_for(ffmpeg_proc.stdout.read(4096), timeout=5) 
            
            if not chunk:
                break
            
            # Invia ai client connessi
            if clients[CAMERA_NAME]:
                await asyncio.gather(*(client.send(chunk) for client in clients[CAMERA_NAME]))

        except asyncio.TimeoutError:
            if ffmpeg_proc.returncode is not None:
                break # FFMPEG è morto
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"[FFMPEG:{CAMERA_NAME}] Errore: {e}")
            break

    logging.warning(f"[FFMPEG] FFMPEG terminato per {CAMERA_NAME}")


# Funzione di avvio (non prende parametri)
async def run_camera():
    global ffmpeg_proc
    
    async def specific_ws_handler(websocket):
        # Chiama ws_handler, passando SOLO il websocket e ignorando 'path'
        await ws_handler(websocket) 

    # Start WebSocket server (passando la funzione wrapper esplicita)
    # ws_handler è la funzione che ora usi al posto della lambda
    server = await websockets.serve(specific_ws_handler, 
                                    "0.0.0.0", WS_PORT, max_size=None)
    logging.info(f"[WS] Server pronto per {CAMERA_NAME} su ws://0.0.0.0:{WS_PORT}")
    
    relay_task = asyncio.create_task(ffmpeg_relay_loop())

    try:
        await relay_task
    finally:
        
        if clients[CAMERA_NAME]:
            logging.info(f"[WS] Forzo la chiusura di {len(clients[CAMERA_NAME])} connessioni attive.")
            # Chiudi tutte le connessioni in parallelo
            await asyncio.gather(*(client.close() for client in clients[CAMERA_NAME]), return_exceptions=True)
            clients[CAMERA_NAME].clear()
            
        # Pulizia FFMPEG e WS server (gestisce il terminale rotto)
        if ffmpeg_proc and ffmpeg_proc.returncode is None:
            logging.info(f"[CLEANUP] Terminazione forzata di FFMPEG per {CAMERA_NAME}")
            ffmpeg_proc.terminate()
            
        server.close()
        await server.wait_closed()
        logging.info(f"[WS] Server per {CAMERA_NAME} chiuso") # <--- ORA DEVE STAMPARE!

        # 4. Uscita con codice di errore se il relay è terminato da solo (per riavvio Docker)
        if relay_task.done() and not relay_task.cancelled() and relay_task.exception() is not None:
             # Uscita con errore se c'è stata un'eccezione non gestita nel relay_task
             logging.error(f"Il servizio {CAMERA_NAME} termina per errore interno, riavvio Docker in corso.")
             sys.exit(1)
        elif relay_task.done() and not relay_task.cancelled():
             # Se è terminato senza eccezione (es. FFmpeg è uscito pulito), potremmo comunque forzare il riavvio
             logging.warning(f"Il relay è terminato. Forzo l'uscita per riavvio Docker.")
             sys.exit(1)

if __name__ == "__main__":
    try:
        logging.info(f"Avvio {CAMERA_NAME} relay (porta {WS_PORT})")
        asyncio.run(run_camera())
    except KeyboardInterrupt:
        logging.info("Interrotto da utente")