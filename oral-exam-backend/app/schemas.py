from pydantic import BaseModel, Field
from typing import List


class StartExamRequest(BaseModel):
    user_id: str


class StartExamResponse(BaseModel):
    session_id: str
    question_text: str
    audio_url: str = ""


class ScoreBlock(BaseModel):
    clarity: int = Field(ge=0, le=10)
    completeness: int = Field(ge=0, le=10)
    confidence: int = Field(ge=0, le=10)


class FeedbackBlock(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    overall: str


class AnswerAudioResponse(BaseModel):
    session_id: str
    transcript: str
    scores: ScoreBlock
    feedback: FeedbackBlock
    next_question_text: str
    audio_url: str = ""


class EndExamResponse(BaseModel):
    session_id: str
    overall_preparation: float
    summary: str
    audio_url: str = ""