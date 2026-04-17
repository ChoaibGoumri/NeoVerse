import os
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.services.gemini_service import gemini_service
from app.services.stt_service import stt_service
from app.services.storage_service import storage_service
from app.services.tts_service import tts_service

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def _load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_exam(user_id: str, subject: str, language: str) -> dict:
    """Start a new exam session: generate professor intro + first question."""
    session_id = str(uuid.uuid4())

    system_prompt = _load_prompt("professor.txt").format(
        language=language, subject=subject
    )
    user_prompt = (
        f"L'esame orale di {subject} sta iniziando. "
        f"Presentati brevemente come tutor e fai la prima domanda allo studente. "
        f"Rispondi in {language}."
    )

    question_text = gemini_service.generate_professor_message(
        system_prompt, user_prompt
    )

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "subject": subject,
        "language": language,
        "created_at": _now_iso(),
        "status": "active",
        "turns": [
            {
                "turn_number": 1,
                "role": "professor",
                "text": question_text,
                "timestamp": _now_iso(),
            }
        ],
    }

    storage_service.save_session(session_id, session_data)

    audio_filename = f"{session_id}_start.mp3"
    audio_url = tts_service.generate_audio(question_text, audio_filename)

    return {"session_id": session_id, "question_text": question_text, "audio_url": audio_url}


def answer_audio(
    user_id: str,
    session_id: str,
    subject: str,
    language: str,
    audio_path: str,
) -> dict:
    """Process a student audio answer: transcribe, evaluate, generate next question."""
    session = storage_service.load_session(session_id)

    # Transcribe audio
    transcript = stt_service.transcribe(audio_path, language)

    # Find last professor question
    last_question = ""
    for turn in reversed(session["turns"]):
        if turn["role"] == "professor":
            last_question = turn["text"]
            break

    next_turn_number = len(session["turns"]) + 1

    # Add student turn
    session["turns"].append(
        {
            "turn_number": next_turn_number,
            "role": "student",
            "text": transcript,
            "timestamp": _now_iso(),
            "audio_file": audio_path,
        }
    )

    # Evaluate answer with Gemini
    eval_system_prompt = _load_prompt("evaluator.txt").format(
        language=language,
        subject=subject,
        question=last_question,
        answer=transcript,
    )

    evaluation = gemini_service.evaluate_answer(
        eval_system_prompt,
        "Valuta la risposta e genera la prossima domanda. Rispondi SOLO con JSON valido.",
    )

    scores = evaluation.get("scores", {"clarity": 0, "completeness": 0, "confidence": 0})
    feedback = evaluation.get(
        "feedback",
        {"strengths": [], "weaknesses": [], "overall": "Valutazione non disponibile."},
    )
    next_question_text = evaluation.get(
        "next_question_text", "Proseguiamo con la prossima domanda."
    )

    # Clamp scores to 0-10
    for key in ("clarity", "completeness", "confidence"):
        val = scores.get(key, 0)
        scores[key] = max(0, min(10, int(val)))

    # Add evaluation turn
    session["turns"].append(
        {
            "turn_number": next_turn_number + 1,
            "role": "evaluation",
            "scores": scores,
            "feedback": feedback,
            "timestamp": _now_iso(),
        }
    )

    # Add next professor question turn
    session["turns"].append(
        {
            "turn_number": next_turn_number + 2,
            "role": "professor",
            "text": next_question_text,
            "timestamp": _now_iso(),
        }
    )

    storage_service.save_session(session_id, session)

    audio_filename = f"{session_id}_{next_turn_number + 2}.mp3"
    audio_url = tts_service.generate_audio(next_question_text, audio_filename)

    return {
        "session_id": session_id,
        "transcript": transcript,
        "scores": scores,
        "feedback": feedback,
        "next_question_text": next_question_text,
        "audio_url": audio_url,
    }


def end_exam(user_id: str, session_id: str) -> dict:
    """End the exam: compute overall score and generate a supportive final summary."""
    session = storage_service.load_session(session_id)

    # Collect all evaluation turns
    eval_turns = [t for t in session["turns"] if t["role"] == "evaluation"]

    if not eval_turns:
        overall_preparation = 0.0
        summary = "Nessuna risposta valutata durante l'esame."
    else:
        all_scores = []
        for et in eval_turns:
            s = et.get("scores", {})
            avg = (
                s.get("clarity", 0) + s.get("completeness", 0) + s.get("confidence", 0)
            ) / 3.0
            all_scores.append(avg)
        overall_preparation = round(sum(all_scores) / len(all_scores), 1)

        # Generate a supportive final summary with Gemini
        subject = session.get("subject", "")
        language = session.get("language", "it-IT")
        n_questions = len(eval_turns)

        summary_system = (
            "Sei un tutor universitario che ha appena terminato una simulazione di esame orale. "
            "Devi fornire un riepilogo finale allo studente. "
            "Sii sempre incoraggiante, professionale e costruttivo. "
            f"Parla in {language}. "
            "Non essere mai duro, umiliante o aggressivo. "
            "Se lo studente ha fatto bene, complimentati sinceramente. "
            "Se lo studente ha aree di miglioramento, spiega chiaramente cosa ripassare senza scoraggiarlo."
        )
        summary_user = (
            f"Materia: {subject}\n"
            f"Numero di domande valutate: {n_questions}\n"
            f"Punteggio medio complessivo: {overall_preparation}/10\n\n"
            "Scrivi un breve riepilogo finale per lo studente (massimo 4-5 frasi). "
            "Includi un commento sulla preparazione complessiva e suggerimenti per migliorare."
        )

        try:
            summary = gemini_service.generate_final_summary(
                summary_system, summary_user
            )
        except Exception:
            summary = (
                f"Esame completato con {n_questions} domande valutate. "
                f"Preparazione complessiva: {overall_preparation}/10."
            )

    session["status"] = "completed"
    storage_service.save_session(session_id, session)

    audio_filename = f"{session_id}_end.mp3"
    audio_url = tts_service.generate_audio(summary, audio_filename)

    return {
        "session_id": session_id,
        "overall_preparation": overall_preparation,
        "summary": summary,
        "audio_url": audio_url,
    }
