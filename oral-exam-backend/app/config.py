from pydantic_settings import BaseSettings, SettingsConfigDict


ALLOWED_SUBJECTS = [
    "Ingegneria del software",
    "Reti di calcolatori",
    "Sistemi operativi",
]


class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 5001

    gemini_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    default_language: str = "it-IT"
    default_subject: str = "Ingegneria del software"

    audio_in_dir: str = "data/audio_in"
    audio_out_dir: str = "data/audio_out"
    sessions_dir: str = "data/sessions"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()