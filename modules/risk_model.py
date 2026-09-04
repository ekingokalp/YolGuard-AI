from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .routing import RouteSummary
from .weather import WeatherSnapshot
from .sun import SunGlare
from .utils import clamp


@dataclass(frozen=True)
class TravelProfile:
    vehicle_type: str
    driver_experience: str
    passenger_count: int  # toplam kişi sayısı: sürücü dahil
    has_baby: bool
    has_child: bool
    has_pet: bool
    max_daily_drive_hours: float
    ev_range_km: float | None = None


@dataclass(frozen=True)
class RiskResult:
    score: float
    category: str
    recommendation: str
    components: dict[str, float]
    reasons: list[str]


def vehicle_capacity(vehicle_type: str) -> int:
    """Demo güvenlik varsayımı olarak toplam kişi kapasitesi döndürür.

    Not: Gerçek araçlarda kapasite ruhsata/koltuk sayısına göre değişebilir. Bu proje,
    kullanıcı girdisini denetlemek ve risk skorunu gerçekçileştirmek için basit varsayımlar kullanır.
    """
    vehicle = vehicle_type.lower()
    if "motosiklet" in vehicle:
        return 2
    if "otomobil" in vehicle:
        return 5
    if "kamyonet" in vehicle or "van" in vehicle:
        return 5
    return 5


def _is_motorcycle(profile: TravelProfile) -> bool:
    return "motosiklet" in profile.vehicle_type.lower()


def _is_rookie(profile: TravelProfile) -> bool:
    return "acemi" in profile.driver_experience.lower()


def _weather_risk(weather: WeatherSnapshot) -> tuple[float, list[str]]:
    reasons: list[str] = []
    risk = 0.0

    rainy_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
    snowy_codes = {71, 73, 75, 77, 85, 86}
    fog_codes = {45, 48}

    if weather.weather_code in rainy_codes:
        risk += 28
        reasons.append(f"Yağışlı hava: {weather.description}.")
    if weather.weather_code in snowy_codes:
        risk += 42
        reasons.append(f"Kar/buzlanma riski: {weather.description}.")
    if weather.weather_code in fog_codes or weather.visibility_m < 4000:
        risk += 28
        reasons.append("Görüş mesafesi düşük olabilir.")
    if weather.precipitation_probability >= 70:
        risk += 20
        reasons.append(f"Yağış olasılığı yüksek: %{weather.precipitation_probability:.0f}.")
    elif weather.precipitation_probability >= 40:
        risk += 10
        reasons.append(f"Yağış olasılığı orta düzeyde: %{weather.precipitation_probability:.0f}.")
    if weather.rain_mm >= 2:
        risk += 14
        reasons.append(f"Saatlik yağmur miktarı dikkat çekici: {weather.rain_mm:.1f} mm.")
    if weather.wind_speed_kmh >= 35 or weather.wind_gusts_kmh >= 55:
        risk += 22
        reasons.append(f"Rüzgâr/gust riski var: {weather.wind_speed_kmh:.0f}/{weather.wind_gusts_kmh:.0f} km/s.")
    elif weather.wind_speed_kmh >= 25 or weather.wind_gusts_kmh >= 40:
        risk += 11
        reasons.append(f"Rüzgâr orta düzeyde: {weather.wind_speed_kmh:.0f}/{weather.wind_gusts_kmh:.0f} km/s.")
    if weather.temperature_c <= 3:
        risk += 16
        reasons.append(f"Düşük sıcaklık/buzlanma ihtimali: {weather.temperature_c:.1f}°C.")
    if weather.temperature_c >= 35:
        risk += 12
        reasons.append(f"Yüksek sıcaklık yorgunluk yaratabilir: {weather.temperature_c:.1f}°C.")

    return clamp(risk), reasons


def _route_risk(route: RouteSummary, target_dt: datetime, max_daily_drive_hours: float) -> tuple[float, list[str]]:
    reasons: list[str] = []
    hours = route.duration_min / 60
    risk = 0.0

    if route.distance_km >= 900:
        risk += 42
        reasons.append(f"Çok uzun rota: {route.distance_km:.0f} km.")
    elif route.distance_km >= 700:
        risk += 35
        reasons.append(f"Çok uzun rota: {route.distance_km:.0f} km.")
    elif route.distance_km >= 350:
        risk += 22
        reasons.append(f"Uzun rota: {route.distance_km:.0f} km.")
    elif route.distance_km >= 150:
        risk += 10
        reasons.append(f"Orta-uzun rota: {route.distance_km:.0f} km.")

    if hours >= max_daily_drive_hours * 2:
        risk += 40
        reasons.append(f"Tahmini sürüş süresi günlük limitin iki katına yaklaşıyor/aşıyor: {hours:.1f} saat.")
    elif hours >= max_daily_drive_hours * 1.5:
        risk += 32
        reasons.append(f"Tahmini sürüş süresi kişisel günlük limitinizin oldukça üzerinde: {hours:.1f} saat.")
    elif hours >= max_daily_drive_hours:
        risk += 24
        reasons.append(f"Tahmini sürüş süresi kişisel günlük limitinizi aşıyor: {hours:.1f} saat.")
    elif hours >= max_daily_drive_hours * 0.75:
        risk += 12
        reasons.append(f"Sürüş süresi günlük limitinize yaklaşıyor: {hours:.1f} saat.")

    if target_dt.hour < 6 or target_dt.hour >= 22:
        risk += 20
        reasons.append("Gece veya çok erken saat sürüşü dikkat gerektirir.")
    elif target_dt.hour in {6, 7, 18, 19, 20}:
        risk += 9
        reasons.append("Geçiş saatlerinde ışık ve trafik koşulları değişken olabilir.")

    return clamp(risk), reasons


def _profile_risk(profile: TravelProfile) -> tuple[float, list[str]]:
    reasons: list[str] = []
    risk = 0.0
    vehicle = profile.vehicle_type.lower()
    experience = profile.driver_experience.lower()
    capacity = vehicle_capacity(profile.vehicle_type)

    if "motosiklet" in vehicle:
        risk += 34
        reasons.append("Motosiklet hava, yol, denge ve yük koşullarından otomobile göre daha fazla etkilenir.")
    elif "kamyonet" in vehicle or "van" in vehicle:
        risk += 12
        reasons.append("Kamyonet/van tipi araçlarda yük dağılımı ve fren mesafesi dikkate alınmalıdır.")
    elif "elektrikli" in vehicle:
        risk += 8
        reasons.append("Elektrikli araçta menzil ve şarj molası planı gerekir.")

    if "acemi" in experience:
        risk += 32
        reasons.append("Sürücü tecrübesi acemi olarak seçildi.")
    elif "orta" in experience:
        risk += 12
        reasons.append("Orta seviye sürüş tecrübesi seçildi.")

    if "motosiklet" in vehicle and "acemi" in experience:
        risk += 18
        reasons.append("Acemi sürücü + motosiklet birleşimi risk katsayısını artırır.")

    if profile.passenger_count > capacity:
        risk += 65
        reasons.append(
            f"Toplam kişi sayısı demo güvenlik kapasitesini aşıyor: {profile.passenger_count}/{capacity}."
        )
    elif profile.passenger_count == capacity and capacity <= 2:
        risk += 10
        reasons.append("Motosiklette iki kişiyle sürüş denge, frenleme ve manevra payını azaltır.")
    elif profile.passenger_count >= 5:
        risk += 10
        reasons.append("Araç doluluğu arttıkça mola, konfor ve dikkat ihtiyacı artar.")
    elif profile.passenger_count >= 3:
        risk += 6
        reasons.append("Kişi sayısı arttıkça mola ve konfor ihtiyacı artar.")

    if profile.has_baby:
        risk += 16
        reasons.append("Bebek ile yolculukta mola, sıcaklık, koltuk ve acil ihtiyaç planı gerekir.")
    if profile.has_child:
        risk += 10
        reasons.append("Çocuk ile yolculukta daha sık mola ve uygun emniyet sistemi gerekir.")
    if profile.has_pet:
        risk += 8
        reasons.append("Evcil hayvan ile yolculukta su, mola ve güvenli taşıma gerekir.")

    if "motosiklet" in vehicle and profile.has_baby:
        risk += 55
        reasons.append("Motosiklet + bebek senaryosu demo güvenlik modelinde uygun görülmez; otomobil önerilir.")
    if "motosiklet" in vehicle and profile.has_child:
        risk += 38
        reasons.append("Motosiklet + çocuk senaryosu için risk çok yükselir; koruma ve güvenli taşıma kısıtlıdır.")
    if "motosiklet" in vehicle and profile.has_pet:
        risk += 25
        reasons.append("Motosiklet + evcil hayvan senaryosu özel taşıma ekipmanı olmadan risklidir.")

    return clamp(risk), reasons


def _ev_risk(profile: TravelProfile, route: RouteSummary) -> tuple[float, list[str]]:
    reasons: list[str] = []
    if "elektrikli" not in profile.vehicle_type.lower():
        return 0.0, reasons
    if not profile.ev_range_km or profile.ev_range_km <= 0:
        return 18.0, ["Elektrikli araç menzili girilmedi; şarj planı belirsiz."]
    usage_ratio = route.distance_km / profile.ev_range_km
    if usage_ratio >= 1.0:
        return 40.0, ["Rota mesafesi araç menzilini aşıyor; şarj molası zorunlu."]
    if usage_ratio >= 0.75:
        return 25.0, ["Rota menzilin %75'inden uzun; şarj molası planlanmalı."]
    if usage_ratio >= 0.55:
        return 12.0, ["Rota menzilin yarısından fazla; güvenlik payı kontrol edilmeli."]
    return 0.0, reasons


def _hard_safety_floor(
    profile: TravelProfile,
    route: RouteSummary,
    weather: WeatherSnapshot,
) -> tuple[float, list[str]]:
    """Bazı kombinasyonlarda ağırlıklı ortalama tek başına yeterli olmaz.

    Örneğin 4 kişi motosiklet seçilirse hava güneş uygun olsa bile yolculuk düşük risk
    çıkmamalıdır. Bu fonksiyon gerçekçiliği artırmak için minimum skor eşiği uygular.
    """
    floors: list[tuple[float, str]] = []
    capacity = vehicle_capacity(profile.vehicle_type)
    hours = route.duration_min / 60
    motorcycle = _is_motorcycle(profile)
    rookie = _is_rookie(profile)

    if profile.passenger_count > capacity:
        floors.append((92.0, f"Kapasite aşımı var: {profile.passenger_count}/{capacity}. Bu senaryo yolculuk için uygun kabul edilmedi."))

    if motorcycle and profile.has_baby:
        floors.append((88.0, "Bebekle motosiklet yolculuğu demo güvenlik modelinde çok yüksek risk kabul edilir."))
    if motorcycle and profile.has_child:
        floors.append((78.0, "Çocukla motosiklet yolculuğu demo güvenlik modelinde yüksek/çok yüksek risk kabul edilir."))
    if motorcycle and profile.has_pet and route.distance_km >= 50:
        floors.append((65.0, "Evcil hayvanla motosiklet yolculuğu uzun rotada yüksek risk kabul edilir."))

    if motorcycle and rookie and route.distance_km >= 700:
        floors.append((85.0, "Acemi motosiklet sürücüsü için 700 km üzeri rota çok yüksek risk kabul edilir."))
    elif motorcycle and rookie and route.distance_km >= 150:
        floors.append((70.0, "Acemi motosiklet sürücüsü için orta/uzun rota yüksek risk kabul edilir."))

    if hours >= profile.max_daily_drive_hours * 2:
        floors.append((78.0, "Sürüş süresi günlük limitin yaklaşık iki katı veya daha fazla."))
    elif hours >= profile.max_daily_drive_hours * 1.5:
        floors.append((68.0, "Sürüş süresi günlük limitin oldukça üzerinde."))

    severe_weather = weather.precipitation_probability >= 70 or weather.wind_gusts_kmh >= 55 or weather.weather_code in {65, 75, 82, 95, 96, 99}
    if motorcycle and severe_weather:
        floors.append((75.0, "Motosiklet ve ağır hava koşulları birlikte yüksek risk kabul edilir."))

    if not floors:
        return 0.0, []
    floor, reason = max(floors, key=lambda item: item[0])
    extra_reasons = [r for _, r in sorted(floors, key=lambda item: item[0], reverse=True)]
    return floor, extra_reasons


def calculate_risk(
    profile: TravelProfile,
    route: RouteSummary,
    weather: WeatherSnapshot,
    sun_glare: SunGlare,
    target_dt: datetime,
) -> RiskResult:
    weather_score, weather_reasons = _weather_risk(weather)
    route_score, route_reasons = _route_risk(route, target_dt, profile.max_daily_drive_hours)
    profile_score, profile_reasons = _profile_risk(profile)
    ev_score, ev_reasons = _ev_risk(profile, route)
    sun_score = sun_glare.risk

    components = {
        "Hava durumu": round(weather_score * 0.25, 1),
        "Rota/süre": round(route_score * 0.25, 1),
        "Sürücü/araç profili": round(profile_score * 0.35, 1),
        "Güneş kamaşması": round(sun_score * 0.10, 1),
        "Elektrikli araç/ek faktör": round(ev_score * 0.05, 1),
    }
    raw_total = clamp(sum(components.values()))

    floor_score, floor_reasons = _hard_safety_floor(profile, route, weather)
    total = max(raw_total, floor_score)
    if total > raw_total:
        components["Güvenlik/kapasite uyumu"] = round(total - raw_total, 1)

    total = clamp(sum(components.values()))

    all_reasons = floor_reasons + weather_reasons + route_reasons + profile_reasons + ev_reasons
    if sun_glare.risk >= 35:
        all_reasons.append(f"{sun_glare.label}: rota-güneş açı farkı {sun_glare.angular_difference_deg:.0f}°, güneş yüksekliği {sun_glare.elevation_deg:.0f}°.")

    # Sırayı koruyarak tekrar eden gerekçeleri kaldır.
    all_reasons = list(dict.fromkeys(all_reasons))

    if total >= 75:
        category = "Çok yüksek"
        recommendation = "Yolculuğu bu koşullarla planlamamanız; kişi/araç uyumunu düzeltmeniz, rotayı bölmeniz veya daha güvenli bir saat/araç seçmeniz önerilir."
    elif total >= 55:
        category = "Yüksek"
        recommendation = "Daha uygun çıkış saati, daha güvenli araç/kişi planı, ek mola ve hazırlık listesiyle risk azaltılmalıdır."
    elif total >= 35:
        category = "Orta"
        recommendation = "Yolculuk yapılabilir; ancak belirtilen risk azaltıcı önlemler dikkate alınmalıdır."
    else:
        category = "Düşük"
        recommendation = "Yolculuk koşulları genel olarak uygun görünüyor. Standart güvenlik hazırlıkları yeterli olabilir."

    return RiskResult(
        score=round(total, 1),
        category=category,
        recommendation=recommendation,
        components=components,
        reasons=all_reasons[:10],
    )
