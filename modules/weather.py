from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import requests

from .utils import nearest_hour_index


WEATHER_CODE_TR = {
    0: "Açık",
    1: "Çoğunlukla açık",
    2: "Parçalı bulutlu",
    3: "Kapalı",
    45: "Sis",
    48: "Kırağılı sis",
    51: "Hafif çisenti",
    53: "Orta çisenti",
    55: "Yoğun çisenti",
    61: "Hafif yağmur",
    63: "Yağmur",
    65: "Şiddetli yağmur",
    71: "Hafif kar",
    73: "Kar",
    75: "Yoğun kar",
    80: "Hafif sağanak",
    81: "Sağanak",
    82: "Şiddetli sağanak",
    95: "Gök gürültülü fırtına",
    96: "Dolu riskli fırtına",
    99: "Şiddetli dolu riskli fırtına",
}


@dataclass(frozen=True)
class WeatherSnapshot:
    description: str
    weather_code: int
    temperature_c: float
    precipitation_probability: float
    rain_mm: float
    wind_speed_kmh: float
    wind_gusts_kmh: float
    visibility_m: float


class WeatherError(RuntimeError):
    pass


def _default_weather() -> WeatherSnapshot:
    return WeatherSnapshot(
        description="Hava verisi alınamadı; orta risk varsayıldı",
        weather_code=3,
        temperature_c=20.0,
        precipitation_probability=30.0,
        rain_mm=0.0,
        wind_speed_kmh=15.0,
        wind_gusts_kmh=25.0,
        visibility_m=10000.0,
    )


def fetch_weather(lat: float, lon: float, target_dt: datetime, timezone: str = "Europe/Istanbul") -> WeatherSnapshot:
    """Open-Meteo saatlik tahmininden hedef saate en yakın hava verisini alır."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability,rain,weather_code,wind_speed_10m,wind_gusts_10m,visibility",
        "forecast_days": 7,
        "timezone": timezone,
    }
    try:
        response = requests.get(url, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        idx = nearest_hour_index(times, target_dt)
        code = int(hourly.get("weather_code", [3])[idx])
        return WeatherSnapshot(
            description=WEATHER_CODE_TR.get(code, f"Kod {code}"),
            weather_code=code,
            temperature_c=float(hourly.get("temperature_2m", [20])[idx]),
            precipitation_probability=float(hourly.get("precipitation_probability", [30])[idx]),
            rain_mm=float(hourly.get("rain", [0])[idx]),
            wind_speed_kmh=float(hourly.get("wind_speed_10m", [15])[idx]),
            wind_gusts_kmh=float(hourly.get("wind_gusts_10m", [25])[idx]),
            visibility_m=float(hourly.get("visibility", [10000])[idx]),
        )
    except Exception:
        return _default_weather()
