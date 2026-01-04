from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import yt_dlp
import os
import uuid
import threading
import time

# ---------------- APP ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- CONFIG ----------------
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FILE_TTL_SECONDS = 600        # delete files after 10 minutes
CLEANUP_INTERVAL = 300        # scan every 5 minutes

# ---------------- UTIL ----------------
def now():
    return int(time.time())

def is_expired(file_path: str, ttl: int):
    return now() - int(os.path.getmtime(file_path)) > ttl

# ---------------- VIDEO DOWNLOAD ----------------
def download_video(file_id: str, url: str, quality: str):
    output_template = f"{DOWNLOAD_DIR}/{file_id}.%(ext)s"

    if quality == "360":
        fmt = "best[ext=mp4][height<=360]"
    elif quality == "720":
        fmt = "best[ext=mp4][height<=720]"
    else:
        fmt = "best[ext=mp4]"

    ydl_opts = {
        "outtmpl": output_template,
        "format": fmt,
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

# ---------------- AUTO CLEANUP WORKER ----------------
def cleanup_worker():
    while True:
        try:
            for filename in os.listdir(DOWNLOAD_DIR):
                path = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.isfile(path) and is_expired(path, FILE_TTL_SECONDS):
                    os.remove(path)
                    print(f"🧹 Auto-deleted expired file: {filename}")
        except Exception as e:
            print("Cleanup error:", e)

        time.sleep(CLEANUP_INTERVAL)

# ---------------- START CLEANUP THREAD ----------------
@app.on_event("startup")
def start_cleanup():
    threading.Thread(target=cleanup_worker, daemon=True).start()

# ---------------- STEP 1: PREPARE ----------------
@app.post("/prepare/mp4")
def prepare_download(url: str = Form(...), quality: str = Form("best")):
    file_id = str(uuid.uuid4())

    threading.Thread(
        target=download_video,
        args=(file_id, url, quality),
        daemon=True
    ).start()

    return {
        "success": True,
        "file_id": file_id
    }

# ---------------- STEP 2: STATUS ----------------
# @app.get("/status/{file_id}")
# def check_status(file_id: str):
#     for filename in os.listdir(DOWNLOAD_DIR):
#         # final merged file only
#         if filename == f"{file_id}.mp4":
#             return {"ready": True}

#     return {"ready": False}

@app.get("/status/{file_id}")
def check_status(file_id: str):
    return {
        "ready": os.path.exists(f"{DOWNLOAD_DIR}/{file_id}.mp4")
    }


# ---------------- STEP 3: DOWNLOAD ----------------
@app.get("/download/{file_id}")
def download_file(file_id: str):
    path = f"{DOWNLOAD_DIR}/{file_id}.mp4"

    if not os.path.exists(path):
        return JSONResponse(
            {"error": "File expired or not ready"},
            status_code=404
        )

    return FileResponse(
        path,
        media_type="video/mp4",
        filename="video.mp4",
        headers={"Content-Disposition": "attachment"}
    )
