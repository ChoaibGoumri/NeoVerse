import json
import os
from typing import Any

from app.config import settings


class StorageService:
    def __init__(self):
        self.sessions_dir = settings.sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)

    def _session_path(self, session_id: str) -> str:
        return os.path.join(self.sessions_dir, f"{session_id}.json")

    def session_exists(self, session_id: str) -> bool:
        return os.path.isfile(self._session_path(session_id))

    def save_session(self, session_id: str, data: dict[str, Any]) -> None:
        path = self._session_path(session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_session(self, session_id: str) -> dict[str, Any]:
        path = self._session_path(session_id)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


storage_service = StorageService()
