from __future__ import annotations

from textwrap import dedent

from .config import CONFIG
from .risk_model import RiskResult, TravelProfile
from .weather import WeatherSnapshot
from .routing import RouteSummary
from .sun import SunGlare
from .expenses import ExpenseEstimate


def _fallback_advice(
    origin: str,
    destination: str,
    departure_label: str,
    risk: RiskResult,
    profile: TravelProfile,
    route: RouteSummary,
    weather: WeatherSnapshot,
    sun_glare: SunGlare,
    checklist: list[str],
    expenses: ExpenseEstimate,
) -> str:
    reasons = "\n".join([f"- {r}" for r in risk.reasons]) or "- Belirgin ek risk saptanmadı."
    top_items = "\n".join([f"- {item}" for item in checklist[:10]])
    return dedent(f"""
    ### YolGuard AI Yolculuk Değerlendirmesi

    **Rota:** {origin} → {destination}  
    **Önerilen/analiz edilen çıkış:** {departure_label}  
    **Tahmini mesafe/süre:** {route.distance_km:.0f} km / {route.duration_min/60:.1f} saat  
    **Risk skoru:** {risk.score:.1f}/100 — **{risk.category}**

    **Genel karar:** {risk.recommendation}

    **Başlıca gerekçeler:**
    {reasons}

    **Hava:** {weather.description}, {weather.temperature_c:.1f}°C, yağış olasılığı %{weather.precipitation_probability:.0f}, rüzgâr {weather.wind_speed_kmh:.0f} km/s.  
    **Güneş etkisi:** {sun_glare.label}; rota-güneş açı farkı {sun_glare.angular_difference_deg:.0f}°.

    **Hazırlık listesi öncelikleri:**
    {top_items}

    **Yaklaşık maliyet:** {expenses.total_cost:,.0f} TL. Bu tutar yakıt/enerji, yemek ve seçildiyse konaklama varsayımlarına göre hesaplanmıştır.

    Bu sonuç kesin trafik veya güvenlik garantisi değildir; karar destek amacıyla üretilmiştir.
    """).strip()


def build_prompt(
    origin: str,
    destination: str,
    departure_label: str,
    risk: RiskResult,
    profile: TravelProfile,
    route: RouteSummary,
    weather: WeatherSnapshot,
    sun_glare: SunGlare,
    checklist: list[str],
    expenses: ExpenseEstimate,
) -> str:
    return dedent(f"""
    Sen YolGuard AI adlı bir yolculuk karar destek uygulamasının Türkçe rapor yazan yapay zekâ modülüsün.
    Görevin kesin hüküm vermek değil, verilen verileri sade, güvenli ve uygulanabilir tavsiyeye dönüştürmektir.

    Veriler:
    - Rota: {origin} -> {destination}
    - Analiz edilen çıkış: {departure_label}
    - Araç tipi: {profile.vehicle_type}
    - Sürücü tecrübesi: {profile.driver_experience}
    - Yolcu sayısı: {profile.passenger_count}
    - Bebek: {profile.has_baby}, çocuk: {profile.has_child}, evcil hayvan: {profile.has_pet}
    - Mesafe: {route.distance_km:.1f} km
    - Süre: {route.duration_min/60:.1f} saat
    - Hava: {weather.description}, sıcaklık {weather.temperature_c:.1f} C, yağış olasılığı %{weather.precipitation_probability:.0f}, rüzgar {weather.wind_speed_kmh:.0f} km/s, gust {weather.wind_gusts_kmh:.0f} km/s
    - Güneş: {sun_glare.label}, güneş azimutu {sun_glare.azimuth_deg}, rota açısı farkı {sun_glare.angular_difference_deg}
    - Risk skoru: {risk.score:.1f}/100, kategori: {risk.category}
    - Risk bileşenleri: {risk.components}
    - Gerekçeler: {risk.reasons}
    - Hazırlık listesi: {checklist}
    - Tahmini maliyet: {expenses.total_cost} TL

    Yanıt formatı:
    1. Kısa karar cümlesi
    2. Nedenler
    3. Risk azaltma önerileri
    4. Yanına alınacak öncelikli 8 madde
    5. Masraf notu

    Türkçe yaz. Gereksiz abartı yapma. Sağlık/güvenlik konusunda kesin garanti verme.
    """).strip()


def generate_ai_advice(
    origin: str,
    destination: str,
    departure_label: str,
    risk: RiskResult,
    profile: TravelProfile,
    route: RouteSummary,
    weather: WeatherSnapshot,
    sun_glare: SunGlare,
    checklist: list[str],
    expenses: ExpenseEstimate,
) -> str:
    """Gemini API varsa yapay zekâ raporu üretir; yoksa şablonlu rapor döndürür."""
    if not CONFIG.gemini_api_key:
        return _fallback_advice(origin, destination, departure_label, risk, profile, route, weather, sun_glare, checklist, expenses)

    try:
        from google import genai

        client = genai.Client(api_key=CONFIG.gemini_api_key)
        response = client.models.generate_content(
            model=CONFIG.gemini_model,
            contents=build_prompt(origin, destination, departure_label, risk, profile, route, weather, sun_glare, checklist, expenses),
        )
        text = getattr(response, "text", None)
        if text and text.strip():
            return text.strip()
    except Exception as exc:
        fallback = _fallback_advice(origin, destination, departure_label, risk, profile, route, weather, sun_glare, checklist, expenses)
        return fallback + f"\n\n> Not: Gemini API çağrısı başarısız oldu, yerel rapor üretildi. Teknik bilgi: {exc}"

    return _fallback_advice(origin, destination, departure_label, risk, profile, route, weather, sun_glare, checklist, expenses)
