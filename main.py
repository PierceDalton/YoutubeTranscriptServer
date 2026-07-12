from fastapi import FastAPI
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL
import re

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
    opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("title", "Unknown Title")


@app.post("/transcript")
def transcript(request: TranscriptRequest):
    video_id = extract_video_id(request.url)

    if not video_id:
        return {
            "success": False,
            "error": "Invalid YouTube URL."
        }

    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=["en", "fi", "sv"])

        full_text = " ".join(snippet.text for snippet in transcript.snippets)

        return {
            "success": True,
            "url": request.url,
            "videoId": video_id,
            "title": get_video_title(request.url),
            "language": transcript.language_code,
            "isGenerated": transcript.is_generated,
            "transcript": full_text
        }

    except Exception as e:
        return {
            "success": False,
            "url": request.url,
            "videoId": video_id,
            "error": str(e)
        }
