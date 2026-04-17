import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers.exam import router as exam_router

app = FastAPI(
    title="Oral Exam Backend",
    version="2.0.0",
    description="AI-powered oral exam simulator backend — powered by Gemini API",
)

# Create required directories on startup
for directory in (settings.audio_in_dir, settings.audio_out_dir, settings.sessions_dir):
    os.makedirs(directory, exist_ok=True)


@app.get("/health")
async def health():
    return {"status": "ok"}

# Monta la cartella audio_out per poter scaricare staticamente i file audio del TTS
app.mount("/audio", StaticFiles(directory=settings.audio_out_dir), name="audio")

app.include_router(exam_router, prefix="/exam", tags=["exam"])