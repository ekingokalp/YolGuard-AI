from __future__ import annotations

from dataclasses import dataclass
import requests

from .geocoding import Location
from .utils import bearing_degrees, haversine_km


@dataclass(frozen=True)
class RouteSummary:
    distance_km: float
    duration_min: float
    geometry: list[tuple[float, float]]  # [(lat, lon), ...]
    start_bearing: float
    midpoint: tuple[float, float]
    raw_provider: str = "OSRM public demo server"


class RoutingError(RuntimeError):
    pass


def _fallback_route(origin: Location, destination: Location) -> RouteSummary:
    """OSRM çalışmazsa demo çökmemesi için kuş uçuşu tabanlı kaba tahmin üretir."""
    straight_km = haversine_km(origin.lat, origin.lon, destination.lat, destination.lon)
    road_km = straight_km * 1.28
    duration_min = (road_km / 75.0) * 60.0
    mid = ((origin.lat + destination.lat) / 2, (origin.lon + destination.lon) / 2)
    return RouteSummary(
        distance_km=round(road_km, 1),
        duration_min=round(duration_min, 0),
        geometry=[(origin.lat, origin.lon), mid, (destination.lat, destination.lon)],
        start_bearing=bearing_degrees(origin.lat, origin.lon, destination.lat, destination.lon),
        midpoint=mid,
        raw_provider="Fallback: kuş uçuşu mesafe x 1.28",
    )


def fetch_route(origin: Location, destination: Location) -> RouteSummary:
    """OSRM public demo server ile sürüş rotası üretir.

    Not: OSRM demo sunucusu garanti SLA vermez; sınıf demosu için yeterlidir.
    Ticari/yoğun kullanımda OpenRouteService, Google Routes API veya self-host OSRM önerilir.
    """
    coords = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
    url = f"https://router.project-osrm.org/route/v1/driving/{coords}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": "false",
        "steps": "false",
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return _fallback_route(origin, destination)
        route = data["routes"][0]
        coordinates = route["geometry"]["coordinates"]
        geometry = [(float(lat), float(lon)) for lon, lat in coordinates]
        # Güneş kamaşması hesabında ilk birkaç sokağın yönü yanıltıcı olabiliyordu.
        # Bu nedenle ana yolculuk yönü için başlangıç-varış arası genel bearing kullanılır.
        start_bearing = bearing_degrees(origin.lat, origin.lon, destination.lat, destination.lon)
        midpoint = geometry[len(geometry) // 2] if geometry else ((origin.lat + destination.lat) / 2, (origin.lon + destination.lon) / 2)
        return RouteSummary(
            distance_km=round(float(route["distance"]) / 1000, 1),
            duration_min=round(float(route["duration"]) / 60, 0),
            geometry=geometry,
            start_bearing=start_bearing,
            midpoint=midpoint,
        )
    except Exception:
        return _fallback_route(origin, destination)
