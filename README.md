# hls_streamer

Converts an RTSP camera feed to a WebSocket stream of MPEG-TS chunks, designed to be consumed by [JSMpeg](https://github.com/phoboslab/jsmpeg) in a browser.

Runs as a Docker container with `restart: always` — the process exits with code 1 on ffmpeg stall or disconnect so Docker restarts it automatically.

## Quick start

```bash
docker run -d --restart always \
  -e CAMERA_NAME=cam1 \
  -e CAMERA_URL=rtsp://user:pass@192.168.1.x:554/stream \
  -e CAMERA_WS_PORT=9000 \
  -p 9000:9000 \
  araroma/hls-streamer:latest
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `CAMERA_URL` | yes | Full RTSP URL of the camera |
| `CAMERA_NAME` | yes | Logical name, used in logs |
| `CAMERA_WS_PORT` | yes | WebSocket port to expose |

## Browser client

Connect with JSMpeg:

```html
<canvas id="feed"></canvas>
<script src="jsmpeg.min.js"></script>
<script>
  new JSMpeg.Player('ws://your-host:9000', { canvas: document.getElementById('feed') });
</script>
```

## Stream parameters

The container transcodes to `mpeg1video` at 480×270, 500 kbps, 20 fps over TCP RTSP transport. Edit `FFMPEG_OUTPUT_OPTIONS` in `ws_streamer.py` to change resolution or bitrate.

## Docker Compose example

```yaml
services:
  cam1:
    image: araroma/hls-streamer:latest
    restart: always
    environment:
      CAMERA_NAME: cam1
      CAMERA_URL: rtsp://user:pass@192.168.1.x:554/stream
      CAMERA_WS_PORT: 9000
    ports:
      - "9000:9000"
```

## Build locally

Requires Python 3.12+, `ffmpeg`, and [`uv`](https://github.com/astral-sh/uv).

```bash
uv sync --locked
CAMERA_NAME=test CAMERA_URL=rtsp://... CAMERA_WS_PORT=9000 uv run python ws_streamer.py
```

## Docker image

Multi-arch (`linux/amd64`, `linux/arm64`) image published to Docker Hub as `araroma/hls-streamer`. CI builds on every push to `main` and tags it `latest`.
