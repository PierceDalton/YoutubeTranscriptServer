from fastapi import FastAPI
from pydantic import BaseModel
from yt_dlp import YoutubeDL
import re
import shutil
import tempfile
import os
import requests
import json

app = FastAPI(title="BURAN YouTube Transcript API")


class TranscriptRequest(BaseModel):
    url: str


@app.get("/")
def home():
    return {"status": "Server is running!"}


def extract_video_id(url: str):

    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
        r"(?:shorts/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        m = re.search(pattern, url)

        if m:
            return m.group(1)

    return None


def get_video_title(url: str):

    opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("title", "Unknown Title")


def get_transcript(url: str):

cookie_path = "/tmp/cookies.txt"

shutil.copy(
    "/etc/secrets/cookies.txt",
    cookie_path
)

    opts = {
        "quiet": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "fi", "sv"],
        "subtitlesformat": "vtt",
        "cookiefile": cookie_path,
        "cachedir": False
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)


    subtitles = info.get("subtitles") or info.get("automatic_captions")

    if not subtitles:
        raise Exception("No subtitles found.")


    selected = None

    for lang in ["en", "fi", "sv"]:

        if lang in subtitles:
            selected = subtitles[lang]
            break


    if not selected:
        selected = list(subtitles.values())[0]


    subtitle_url = selected[0]["url"]


    response = requests.get(subtitle_url)
    response.raise_for_status()

    subtitle_text = response.text


    # Handle JSON3 subtitles
    if subtitle_text.startswith("{"):

        data = json.loads(subtitle_text)

        lines = []

        for event in data.get("events", []):

            for seg in event.get("segs", []):

                text = seg.get("utf8", "")

                if text.strip():
                    lines.append(text.strip())

        return " ".join(lines)


    # Handle VTT subtitles
    lines = []

    for line in subtitle_text.splitlines():

        if (
            line.strip()
            and not line.startswith("WEBVTT")
            and "-->" not in line
            and not line.strip().isdigit()
        ):
            lines.append(line)


    return " ".join(lines)



@app.post("/transcript")
def transcript(request: TranscriptRequest):

    video_id = extract_video_id(request.url)


    if not video_id:

        return {
            "success": False,
            "error": "Invalid YouTube URL."
        }


    try:

        full_text = get_transcript(request.url)


        return {
            "success": True,
            "url": request.url,
            "videoId": video_id,
            "title": get_video_title(request.url),
            "transcript": full_text
        }


    except Exception as e:

        return {
            "success": False,
            "url": request.url,
            "videoId": video_id,
            "error": str(e)
        }
