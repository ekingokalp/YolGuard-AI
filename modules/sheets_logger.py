from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import csv

from .config import CONFIG


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[f"{key}_{sub_key}"] = sub_value
        elif isinstance(value, list):
            flat[key] = " | ".join(map(str, value))
        else:
            flat[key] = value
    return flat


def log_to_csv(row: dict[str, Any], path: str = "logs/yolguard_logs.csv") -> str:
    flat = _flatten_row({"created_at": datetime.now().isoformat(timespec="seconds"), **row})
    file_path = Path(path)
    file_path.parent.mkdir(exist_ok=True)
    write_header = not file_path.exists()
    with file_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(flat)
    return str(file_path)


def log_to_google_sheets(row: dict[str, Any]) -> str | None:
    """Service account ayarlanırsa Google Sheets'e log yazar.

    Aksi halde None döndürür. Bu tasarım uygulamanın ana işleyişini bozmaz.
    """
    if not CONFIG.google_service_account_file:
        return None
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(CONFIG.google_service_account_file, scopes=scopes)
        client = gspread.authorize(credentials)
        try:
            sheet = client.open(CONFIG.google_sheet_name).sheet1
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(CONFIG.google_sheet_name)
            sheet = spreadsheet.sheet1
        flat = _flatten_row({"created_at": datetime.now().isoformat(timespec="seconds"), **row})
        values = list(flat.values())
        if not sheet.get_all_values():
            sheet.append_row(list(flat.keys()))
        sheet.append_row(values)
        return CONFIG.google_sheet_name
    except Exception:
        return None
