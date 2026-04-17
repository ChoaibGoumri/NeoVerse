import json
import logging
import re
import time

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 4
RETRY_BASE_DELAY = 5


class GeminiService:
    """Wrapper around the Google GenAI SDK for Gemini API calls."""

    def __init__(self):
        if not settings.gemini_key:
            raise RuntimeError(
                "GEMINI_KEY is not set. Add it to your .env file."
            )
        self._client = genai.Client(api_key=settings.gemini_key)
        self._model = settings.gemini_model

    def _call_with_retry(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.7
    ) -> str:
        """Call Gemini with automatic retry on transient 503/429 errors."""
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=user_prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=temperature,
                    ),
                )
                text = response.text
                if not text or not text.strip():
                    raise RuntimeError("Gemini returned an empty response.")
                return text.strip()
            except Exception as exc:
                last_error = exc
                exc_str = str(exc)
                is_retryable = any(
                    kw in exc_str
                    for kw in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded")
                )
                if is_retryable and attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * attempt  # exponential-ish backoff
                    logger.warning(
                        "Gemini transient error on attempt %d/%d — retrying in %ds... (%s)",
                        attempt, MAX_RETRIES, delay, exc_str[:120],
                    )
                    time.sleep(delay)
                    continue
                raise
        raise last_error  # type: ignore[misc]

    def generate_professor_message(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate the professor's intro + first question or follow-up."""
        return self._call_with_retry(system_prompt, user_prompt, temperature=0.7)

    def evaluate_answer(
        self, system_prompt: str, user_prompt: str
    ) -> dict:
        """Evaluate a student answer. Returns parsed JSON dict."""
        raw = self._call_with_retry(system_prompt, user_prompt, temperature=0.3)
        logger.debug("Gemini evaluator raw response: %s", raw)

        # Strip markdown code fences if present
        cleaned = raw
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        # Extract JSON object
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not json_match:
            raise ValueError(
                f"Gemini evaluation did not return valid JSON. Raw: {raw}"
            )
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Gemini evaluation returned malformed JSON: {exc}. Raw: {raw}"
            ) from exc

    def generate_final_summary(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate a supportive final exam summary."""
        return self._call_with_retry(system_prompt, user_prompt, temperature=0.6)


gemini_service = GeminiService()
