from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from astral import Observer
    from astral.sun import azimuth, elevation
    ASTRAL_AVAILABLE = True
except Exception:
    ASTRAL_AVAILABLE = False

from .utils import angular_difference


@dataclass(frozen=True)
class SunGlare:
    azimuth_deg: float
    elevation_deg: float
    angular_difference_deg: float
    risk: float
    label: str


def _approx_sun_position(target_dt: datetime) -> tuple[float, float]:
    """Astral yoksa basit demo yaklaşımı: sabah doğu, öğlen güney, akşam batı."""
    hour = target_dt.hour + target_dt.minute / 60
    if 6 <= hour <= 18:
        # 06:00 -> 90 derece, 12:00 -> 180 derece, 18:00 -> 270 derece
        az = 90 + (hour - 6) * 15
        elevation_est = max(0, 45 - abs(hour - 12) * 7)
    else:
        az = 0
        elevation_est = -10
    return az, elevation_est


def _elevation_factor(sun_el: float) -> float:
    """Güneş ufka yakınken kamaşma daha kuvvetlidir.

    Önceki sürüm çok dar bir pencere kullanıyordu; bu nedenle sabah/akşam dışında
    her şeyi düşük sayabiliyordu. Bu sürüm 0-35 derece aralığını daha gerçekçi ele alır.
    """
    if sun_el <= -3:
        return 0.0
    if sun_el < 0:
        return 0.15
    if sun_el <= 12:
        return 1.0
    if sun_el <= 30:
        return 1.0 - ((sun_el - 12) / 18) * 0.45  # 12° -> 1.00, 30° -> 0.55
    if sun_el <= 45:
        return 0.55 - ((sun_el - 30) / 15) * 0.45  # 30° -> 0.55, 45° -> 0.10
    if sun_el <= 55:
        return 0.05
    return 0.0


def calculate_sun_glare(
    lat: float,
    lon: float,
    route_bearing_deg: float,
    target_dt: datetime,
    timezone: str = "Europe/Istanbul",
) -> SunGlare:
    """Rota yönü ile güneşin konumunu karşılaştırarak göz alma riskini hesaplar.

    Güneş ufka yakınken ve rota yönü güneşe / güneşin ön yan açısına bakarken risk yükselir.
    """
    try:
        aware_dt = target_dt.replace(tzinfo=ZoneInfo(timezone)) if target_dt.tzinfo is None else target_dt
    except Exception:
        aware_dt = target_dt

    if ASTRAL_AVAILABLE:
        observer = Observer(latitude=lat, longitude=lon)
        sun_az = float(azimuth(observer, aware_dt))
        sun_el = float(elevation(observer, aware_dt))
    else:
        sun_az, sun_el = _approx_sun_position(aware_dt)

    angle_diff = angular_difference(route_bearing_deg, sun_az)

    # 0° tam karşıdan, 90° yandan, 180° arkadan güneş demektir.
    # Önceki sürüm 60° üstünü neredeyse tamamen yok sayıyordu; burada ön-yandan gelen
    # güneşi de kısmi risk kabul ediyoruz.
    direction_factor = max(0.0, (110.0 - angle_diff) / 110.0)
    elevation_factor = _elevation_factor(sun_el)
    risk = min(100.0, 100.0 * direction_factor * elevation_factor)

    # Kritik sabah/akşam anlarında tam karşıya yakın güneşin etkisini minimum seviyeye sabitle.
    if 0 <= sun_el <= 15 and angle_diff <= 25:
        risk = max(risk, 80.0)
    elif 0 <= sun_el <= 20 and angle_diff <= 45:
        risk = max(risk, 60.0)
    elif 0 <= sun_el <= 25 and angle_diff <= 65:
        risk = max(risk, 40.0)

    if risk >= 70:
        label = "Yüksek güneş kamaşması riski"
    elif risk >= 35:
        label = "Orta güneş kamaşması riski"
    else:
        label = "Düşük güneş kamaşması riski"

    return SunGlare(
        azimuth_deg=round(sun_az, 1),
        elevation_deg=round(sun_el, 1),
        angular_difference_deg=round(angle_diff, 1),
        risk=round(risk, 1),
        label=label,
    )
