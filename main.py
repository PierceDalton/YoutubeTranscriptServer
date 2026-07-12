from fastapi import FastAPI
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from requests import Session
import re
import os

PROXY_URL = os.getenv("PROXY_URL")

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


def get_transcript(video_id: str):

    session = Session()

    if PROXY_URL:
        print(f"Using proxy: {PROXY_URL}")

        session.proxies = {
            "http": PROXY_URL,
            "https": PROXY_URL
        }

    api = YouTubeTranscriptApi(http_client=session)

    transcript = api.fetch(video_id)

    return " ".join(
        snippet.text
        for snippet in transcript
    )


@app.post("/transcript")
def transcript(request: TranscriptRequest):

    video_id = extract_video_id(request.url)

    if not video_id:
        return {
            "success": False,
            "error": "Invalid YouTube URL."
        }

    try:
        full_text = get_transcript(video_id)

        return {
            "success": True,
            "url": request.url,
            "videoId": video_id,
            "transcript": full_text
        }

    except Exception as e:
        return {
            "success": False,
            "url": request.url,
            "videoId": video_id,
            "error": str(e)
        }
