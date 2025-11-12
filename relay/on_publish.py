from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio, subprocess, os, urllib.parse, threading, time
import logging, json
from fastapi.responses import JSONResponse
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

app = FastAPI()

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

YOUTUBE_URL = os.getenv("YOUTUBE_RTMP_URL", "rtmp://a.rtmp.youtube.com/live2")
VIDEOS_DIR = os.getenv("VIDEOS_DIR", "./videos")
NGINX_HOST = os.getenv("NGINX_HOST", "nginx_rtmp")
STREAMING_ENDPOINT = os.getenv("STREAMING_ENDPOINT", "live")
RTMP_PORT = 1935
NGINX_URL = f"rtmp://{NGINX_HOST}:{RTMP_PORT}/{STREAMING_ENDPOINT}"

DIRECTUS_URL = "http://directus:8055/items/Giramelle_Streams?limit=-1"

# -----------------------------------------------------------------------------
# STATE
# -----------------------------------------------------------------------------

stream_status = {}     # stream_key → { filename, status }
stream_procs = {}      # stream_key → ffmpeg input process
active_streams = {}    # stream_key → youtube push thread
clients = set()        # connected websockets

# -----------------------------------------------------------------------------
# MIDDLEWARE
# -----------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

async def notify_clients():
    """Broadcast current state."""
    if not clients:
        return

    msg = json.dumps(stream_status)
    remove = []

    for ws in clients:
        try:
            await ws.send_text(msg)
        except:
            remove.append(ws)

    for ws in remove:
        clients.remove(ws)

def start_ffmpeg(stream_key: str, filename: str):
    """Start ffmpeg feeder → NGINX."""
    input_path = os.path.join(VIDEOS_DIR, filename)
    rtmp_url = f"{NGINX_URL}/{stream_key}"

    cmd = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-i", input_path,
        "-c", "copy",
        "-f", "flv",
        rtmp_url
    ]

    logging.info(f"[FEEDER] {stream_key} → {rtmp_url}")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def youtube_push_loop(stream_key: str, target_url: str):
    """Push stream from nginx to YouTube with auto reconnect."""
    delay = 5
    max_delay = 300

    while True:

        # ✅ STOP CONDITION: /on_done removed this key
        if stream_key not in active_streams:
            logging.info(f"[YT-PUSH] {stream_key} stopped externally (on_done).")
            return

        logging.info(f"[YT-PUSH] {stream_key} → {target_url}")

        cmd = [
            "ffmpeg",
            "-re",
            "-i", f"{NGINX_URL}/{stream_key}",
            "-c", "copy",
            "-f", "flv",
            "-reconnect_on_network_error", "1",
            "-reconnect_on_http_error", "4xx,5xx",
            target_url
        ]

        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        exit_code = p.wait()

        if exit_code == 0:
            logging.info(f"[YT-PUSH] {stream_key} finished normally.")
            break

        logging.warning(f"[YT-PUSH] {stream_key} failed, retrying in {delay}s...")
        time.sleep(delay)
        delay = min(delay * 2, max_delay)

# -----------------------------------------------------------------------------
# WEBSOCKET
# -----------------------------------------------------------------------------

@app.websocket("/ws")
async def ws_status(ws: WebSocket):
    await ws.accept()
    clients.add(ws)

    # send initial state
    await ws.send_text(json.dumps(stream_status))

    try:
        while True:
            await ws.receive_text()  # not used, keeps socket open
    except:
        pass
    finally:
        clients.remove(ws)

# -----------------------------------------------------------------------------
# RTMP HOOKS
# -----------------------------------------------------------------------------

@app.post("/on_publish")
async def on_publish(request: Request):
    body = (await request.body()).decode()
    data = {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}
    stream_key = data.get("name")

    logging.info(f"[on_publish] {stream_key} published")

    if stream_key in stream_status:
        stream_status[stream_key]["status"] = "playing"
        await notify_clients()

    # start youtube push thread
    if stream_key not in active_streams:
        t = threading.Thread(
            target=youtube_push_loop,
            args=(stream_key, f"{YOUTUBE_URL}/{stream_key}"),
            daemon=True
        )
        active_streams[stream_key] = t
        t.start()

    return {"ok": True}

@app.post("/on_done")
async def on_done(request: Request):
    body = (await request.body()).decode()
    data = {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}
    stream_key = data.get("name")

    logging.info(f"[on_done] {stream_key} ended")

    active_streams.pop(stream_key, None)

    if stream_key in stream_status:
        stream_status[stream_key]["status"] = "stopped"
        await notify_clients()

    return {"ok": True}


# -----------------------------------------------------------------------------
# CONTROL ENDPOINTS
# -----------------------------------------------------------------------------

@app.post("/start/{stream_key}")
async def start_stream_post(stream_key: str):
    if stream_key not in stream_status:
        return JSONResponse({"error": "Unknown stream"}, status_code=404)

    if stream_key in stream_procs:
        return JSONResponse({"info": "Already running"}, status_code=200)

    filename = stream_status[stream_key]["filename"]

    try:
        p = start_ffmpeg(stream_key, filename)
        stream_procs[stream_key] = p
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/stop/{stream_key}")
async def stop_stream_post(stream_key: str):
    if stream_key not in stream_procs:
        return JSONResponse({"error": "Not running"}, status_code=400)

    p = stream_procs.pop(stream_key)
    p.terminate()

    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()

    return {"ok": True}

@app.post("/start_all")
async def start_all():
    results = {}

    for key, info in stream_status.items():
        if info["status"] != "playing":
            resp = await start_stream_post(key)
            results[key] = "started"
            await asyncio.sleep(1)

    return results

@app.post("/stop_all")
async def stop_all():
    results = {}

    for key in list(stream_procs.keys()):
        resp = await stop_stream_post(key)
        results[key] = "stopped"
        await asyncio.sleep(1)

    return results

# -----------------------------------------------------------------------------
# STREAM LOADING FROM DIRECTUS
# -----------------------------------------------------------------------------

@app.post("/api/streams")
async def api_streams():
    return await load_streams_from_directus()

async def load_streams_from_directus():
    async with httpx.AsyncClient() as c:
        r = await c.get(DIRECTUS_URL)
        data = r.json()["data"]

    streams = []

    for s in data:
        key = s["Stream_Key"]

        if key not in stream_status:
            stream_status[key] = {"filename": s["URL"], "status": "stopped"}
        else:
            stream_status[key]["filename"] = s["URL"]

        streams.append({
            "id": str(s["id"]),
            "stream_key": key,
            "name": s.get("Name") or key,
            "filename": s["URL"],
            "language": s.get("Language", "unknown"),
            "avatar": f"http://localhost:8055/assets/{s['Avatar']}" if s.get("Avatar") else None,
            "status": stream_status[key]["status"]
        })

    return JSONResponse(streams)
