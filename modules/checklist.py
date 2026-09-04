from __future__ import annotations

from .risk_model import TravelProfile, RiskResult
from .weather import WeatherSnapshot
from .routing import RouteSummary


def build_checklist(profile: TravelProfile, risk: RiskResult, weather: WeatherSnapshot, route: RouteSummary) -> list[str]:
    items = [
        "Kimlik, ehliyet, ruhsat ve sigorta bilgileri",
        "Telefon şarj cihazı / powerbank",
        "Su ve hafif atıştırmalık",
        "Navigasyon için telefon tutucu veya güvenli sabitleme",
        "Temel ilk yardım seti",
    ]

    vehicle = profile.vehicle_type.lower()
    if "motosiklet" in vehicle:
        items.extend([
            "Tam korumalı motosiklet ekipmanı: kask, mont, eldiven, pantolon, bot",
            "Yağmurluk veya su geçirmez dış katman",
            "Kask vizörü temizliği için mikrofiber bez",
            "Lastik basıncı ve fren kontrolü",
        ])
    else:
        items.extend([
            "Lastik basıncı ve yedek lastik/tamir kiti kontrolü",
            "Cam suyu, silecek ve far kontrolü",
        ])

    if "elektrikli" in vehicle:
        items.extend([
            "Şarj kablosu ve adaptör kontrolü",
            "Menzil güvenlik payı ve olası şarj molası planı",
        ])

    if weather.precipitation_probability >= 40 or weather.weather_code in {61, 63, 65, 80, 81, 82, 95, 96, 99}:
        items.extend([
            "Yağış için yedek kıyafet / kuru çorap",
            "Su geçirmez çanta veya poşet",
        ])
    if weather.temperature_c >= 30:
        items.extend([
            "Ek su ve güneş koruması",
            "Sıcak saatlerde daha sık mola planı",
        ])
    if weather.temperature_c <= 8:
        items.extend([
            "Termal katman veya sıcak tutan kıyafet",
            "Soğuk hava için eldiven/yedek katman",
        ])

    if profile.has_baby:
        items.extend([
            "Bebek bezi, ıslak mendil, yedek kıyafet",
            "Bebek maması/süt, biberon ve sıcaklık kontrolü",
            "Bebek koltuğu bağlantı kontrolü",
        ])
    if profile.has_child:
        items.extend([
            "Çocuk için su, atıştırmalık ve eğlence malzemesi",
            "Çocuk koltuğu veya emniyet kemeri kontrolü",
        ])
    if profile.has_pet:
        items.extend([
            "Evcil hayvan taşıma çantası/emniyet aparatı",
            "Mama, su kabı ve dışkı poşeti",
        ])

    if route.duration_min / 60 >= 4:
        items.append("Her 2 saatte bir mola planı")
    if risk.score >= 55:
        items.append("Alternatif çıkış saati ve erteleme planı")

    # Sırayı koruyarak tekrarları kaldır.
    return list(dict.fromkeys(items))
