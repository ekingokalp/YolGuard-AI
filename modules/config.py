from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    nominatim_user_agent: str = os.getenv(
        "NOMINATIM_USER_AGENT",
        "YolGuardAI-StudentProject/1.0 (student-project@example.com)",
    )
    google_service_account_file: str | None = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or None
    google_sheet_name: str = os.getenv("GOOGLE_SHEET_NAME", "YolGuardAI_Logs")


CONFIG = AppConfig()
