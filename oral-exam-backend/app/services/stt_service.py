from faster_whisper import WhisperModel

LANGUAGE_MAP = {
    "it-IT": "it",
    "en-US": "en",
    "es-ES": "es",
    "fr-FR": "fr",
}


class STTService:
    def __init__(self, model_size: str = "small"):
        self._model_size = model_size
        self._model: WhisperModel | None = None

    @property
    def model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                self._model_size, device="cpu", compute_type="int8"
            )
        return self._model

    def transcribe(self, audio_path: str, language: str) -> str:
        lang_code = LANGUAGE_MAP.get(language, language.split("-")[0].lower())
        segments, _info = self.model.transcribe(
            audio_path,
            language=lang_code,
            vad_filter=True,
        )
        text = " ".join(segment.text.strip() for segment in segments)
        return text


stt_service = STTService()