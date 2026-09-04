from __future__ import annotations

import math
from datetime import datetime
from typing import Iterable


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki koordinat arasındaki kuş uçuşu mesafeyi km cinsinden döndürür."""
    radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Başlangıçtan varışa yaklaşık rota yönünü derece olarak verir. 0=Kuzey, 90=Doğu."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    theta = math.degrees(math.atan2(x, y))
    return (theta + 360) % 360


def angular_difference(a: float, b: float) -> float:
    """İki açı arasındaki en küçük farkı derece olarak verir."""
    return abs((a - b + 180) % 360 - 180)


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def nearest_hour_index(times: list[str], target_dt: datetime) -> int:
    """Open-Meteo saat dizisinde hedef zamana en yakın indexi bulur."""
    if not times:
        return 0
    target_key = target_dt.strftime("%Y-%m-%dT%H:00")
    if target_key in times:
        return times.index(target_key)
    parsed = []
    for i, item in enumerate(times):
        try:
            parsed.append((abs(datetime.fromisoformat(item) - target_dt.replace(minute=0, second=0, microsecond=0)), i))
        except ValueError:
            continue
    return min(parsed, key=lambda x: x[0])[1] if parsed else 0
