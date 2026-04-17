import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings, ALLOWED_SUBJECTS
from app.schemas import AnswerAudioResponse, EndExamResponse, StartExamRequest, StartExamResponse
from app.services import exam_service
from app.services.storage_service import storage_service

router = APIRouter()


@router.post("/start", response_model=StartExamResponse)
async def start_exam(payload: StartExamRequest):
    # Validate subject
    if payload.subject not in ALLOWED_SUBJECTS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Materia non valida: '{payload.subject}'. "
                f"Le materie supportate sono: {', '.join(ALLOWED_SUBJECTS)}"
            ),
        )

    try:
        result = exam_service.start_exam(
            user_id=payload.user_id,
            subject=payload.subject,
            language=payload.language,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/answer-audio", response_model=AnswerAudioResponse)
async def answer_audio(
    user_id: str = Form(...),
    session_id: str = Form(...),
    subject: str = Form(...),
    language: str = Form(...),
    audio: UploadFile = File(...),
):
    # Validate session exists
    if not storage_service.session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    # Save uploaded audio
    audio_dir = settings.audio_in_dir
    os.makedirs(audio_dir, exist_ok=True)
    audio_filename = f"{session_id}_{audio.filename}"
    audio_path = os.path.join(audio_dir, audio_filename)

    content = await audio.read()
    with open(audio_path, "wb") as f:
        f.write(content)

    try:
        result = exam_service.answer_audio(
            user_id=user_id,
            session_id=session_id,
            subject=subject,
            language=language,
            audio_path=audio_path,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/end", response_model=EndExamResponse)
async def end_exam(user_id: str, session_id: str):
    if not storage_service.session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")

    try:
        result = exam_service.end_exam(user_id=user_id, session_id=session_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc