# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

RTSP-to-WebSocket streamer. ffmpeg reads an RTSP camera feed, transcodes to MPEG-TS (`mpeg1video`), and the Python asyncio server pipes chunks over WebSocket to connected browsers. Designed to run as a Docker container with `restart: always` — the app deliberately calls `sys.exit(1)` to trigger Docker restart on ffmpeg stall or exit.

`entrypoint.sh` is an older HLS variant (ffmpeg → `.m3u8` segments → `http.server`) and is **not used by the Dockerfile**.

## Environment variables

| Var | Description |
|---|---|
| `CAMERA_NAME` | Logical camera identifier (used in logs and client dict key) |
| `CAMERA_URL` | Full RTSP URL, e.g. `rtsp://user:pass@192.168.x.x:554/...` |
| `CAMERA_WS_PORT` | WebSocket port exposed by the server (default intent: 9000) |

## Run locally

```bash
# Install deps
uv sync --locked

# Run (requires ffmpeg installed on the host)
CAMERA_NAME=test CAMERA_URL=rtsp://... CAMERA_WS_PORT=9000 uv run python ws_streamer.py
```

## Docker

```bash
# Build
docker build -t hls-streamer .

# Run
docker run --restart always \
  -e CAMERA_NAME=cam1 \
  -e CAMERA_URL=rtsp://... \
  -e CAMERA_WS_PORT=9000 \
  -p 9000:9000 \
  hls-streamer
```

## CI / Docker Hub

GitHub Actions (`.github/workflows/docker-build.yml`) builds multi-arch (`linux/amd64`, `linux/arm64`) and pushes to `araroma/hls-streamer` on:
- push to `main` or `beta`
- PR with label `build-docker` (label is auto-removed after build)

Tag `latest` is set only on `main` pushes.

## Stall detection logic

`ffmpeg_relay_loop()` reads stdout with a 5s timeout. After **3 consecutive timeouts** (15s of silence) it breaks the loop. `run_camera()` then calls `sys.exit(1)` so Docker restarts the container. This is the intentional recovery path — don't add retry logic inside the process.
