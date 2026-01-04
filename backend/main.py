from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
import yt_dlp
import os
import uuid

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.post("/download/mp4")
async def download_mp4(
    url: str = Form(...),
    quality: str = Form("best")
):
    file_id = str(uuid.uuid4())
    output_template = f"{DOWNLOAD_DIR}/{file_id}.%(ext)s"

    if quality == "360":
        format_selector = "bestvideo[height<=360]+bestaudio/best[height<=360]"
    elif quality == "720":
        format_selector = "bestvideo[height<=720]+bestaudio/best[height<=720]"
    else:
        format_selector = "bestvideo+bestaudio/best"

    ydl_opts = {
        "outtmpl": output_template,
        "format": format_selector,
        "merge_output_format": "mp4",
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_file = f"{DOWNLOAD_DIR}/{file_id}.mp4"

        return FileResponse(
            final_file,
            filename=f"{info.get('title')}.mp4",
            media_type="video/mp4"
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
