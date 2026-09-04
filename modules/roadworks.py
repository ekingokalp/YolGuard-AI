from __future__ import annotations

from pathlib import Path
import csv
from dataclasses import dataclass

from .utils import haversine_km


@dataclass(frozen=True)
class RoadworkHit:
    name: str
    distance_to_route_km: float
    severity: str
    note: str


def load_demo_roadworks(path: str = "data/demo_roadworks.csv") -> list[dict[str, str]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_nearby_roadworks(route_geometry: list[tuple[float, float]], max_distance_km: float = 25.0) -> list[RoadworkHit]:
    """Demo yol çalışması verisini rotaya yakınlıkla eşleştirir.

    Gerçek projede bu CSV Google Sheets ya da belediye/KGM veri kaynağıyla güncellenebilir.
    """
    roadworks = load_demo_roadworks()
    if not roadworks or not route_geometry:
        return []

    # Performans için tüm rota yerine örneklenmiş noktaları kullanıyoruz.
    step = max(1, len(route_geometry) // 80)
    sampled = route_geometry[::step]
    hits: list[RoadworkHit] = []
    for rw in roadworks:
        try:
            rw_lat = float(rw["lat"])
            rw_lon = float(rw["lon"])
            min_distance = min(haversine_km(rw_lat, rw_lon, lat, lon) for lat, lon in sampled)
            if min_distance <= max_distance_km:
                hits.append(
                    RoadworkHit(
                        name=rw["name"],
                        distance_to_route_km=round(min_distance, 1),
                        severity=rw.get("severity", "orta"),
                        note=rw.get("note", ""),
                    )
                )
        except Exception:
            continue
    return sorted(hits, key=lambda x: x.distance_to_route_km)
