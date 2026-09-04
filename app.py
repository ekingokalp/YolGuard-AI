from __future__ import annotations

from datetime import datetime, date, time
import html
import json

import pandas as pd
import streamlit as st

from modules.ai_advisor import generate_ai_advice
from modules.checklist import build_checklist
from modules.expenses import estimate_expenses
from modules.geocoding import geocode_address, GeocodingError
from modules.risk_model import TravelProfile, calculate_risk, vehicle_capacity
from modules.routing import fetch_route
from modules.roadworks import find_nearby_roadworks
from modules.sheets_logger import log_to_csv, log_to_google_sheets
from modules.sun import calculate_sun_glare
from modules.weather import fetch_weather

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except Exception:
    FOLIUM_AVAILABLE = False


st.set_page_config(
    page_title="YolGuard AI",
    page_icon="🛡️",
    layout="wide",
)


VEHICLES = ["Otomobil", "Motosiklet", "Elektrikli otomobil", "Kamyonet / van"]
EXPERIENCE = ["Acemi", "Orta", "Deneyimli"]
DEFAULT_HOURS = ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]


CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.6rem;}
.hero {
  background: linear-gradient(135deg, #e0f2fe 0%, #f8fafc 70%);
  border: 1px solid #dbeafe;
  border-radius: 18px;
  padding: 22px 26px;
  margin-bottom: 18px;
}
.hero h1 {margin: 0; font-size: 2.2rem; color: #0f172a;}
.hero p {font-size: 1.05rem; color: #334155; margin-bottom: 0;}
.risk-low {color:#166534;font-weight:700;}
.risk-mid {color:#a16207;font-weight:700;}
.risk-high {color:#b91c1c;font-weight:700;}
.card {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 16px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.small-note {color:#64748b; font-size:0.9rem;}
.component-row {margin: 0.45rem 0 0.8rem 0;}
.component-label {font-weight: 600; color: #334155; margin-bottom: 0.25rem;}
.component-track {height: 16px; background: #e5e7eb; border-radius: 999px; overflow: hidden;}
.component-fill {height: 16px; background: #38bdf8; border-radius: 999px;}
.component-value {font-size: 0.85rem; color: #475569; margin-top: 0.15rem;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
      <h1>🛡️ YolGuard AI</h1>
      <p>Kişiselleştirilmiş yolculuk risk skorlama, çıkış saati karşılaştırması ve yapay zekâ destekli hazırlık asistanı.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ Proje Bilgisi")
    st.write("Bu uygulama navigasyon uygulaması değildir; yolculuk öncesi karar destek sistemi olarak tasarlanmıştır.")
    st.caption("Veri kaynakları: Yerel Türkiye koordinat tabanı, Nominatim/Photon/Open-Meteo geocoding, OSRM, Open-Meteo, Astral. AI: Opsiyonel Gemini API.")
    st.divider()
    st.subheader("Risk kategorileri")
    st.write("0–34: Düşük")
    st.write("35–54: Orta")
    st.write("55–74: Yüksek")
    st.write("75–100: Çok yüksek")
    st.divider()
    if st.button("Son analizi temizle", use_container_width=True):
        st.session_state.pop("analysis_result", None)
        st.rerun()


if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None


def _parse_time_label(label: str) -> time:
    hour, minute = label.split(":")
    return time(int(hour), int(minute))


def _category_class(score: float) -> str:
    if score >= 55:
        return "risk-high"
    if score >= 35:
        return "risk-mid"
    return "risk-low"


def _render_component_bars(components: dict[str, float]) -> None:
    """Streamlit/Altair sürüm uyumsuzluklarından etkilenmeyen basit HTML bar görünümü."""
    if not components:
        st.info("Risk bileşeni bulunamadı.")
        return
    max_value = max(max(components.values()), 1)
    rows = []
    for label, value in sorted(components.items(), key=lambda item: item[1], reverse=True):
        width = min(max((float(value) / max_value) * 100, 0), 100)
        safe_label = html.escape(str(label))
        safe_value = html.escape(f"{float(value):.1f} puan")
        rows.append(
            f"""
            <div class="component-row">
              <div class="component-label">{safe_label}</div>
              <div class="component-track"><div class="component-fill" style="width:{width:.1f}%"></div></div>
              <div class="component-value">{safe_value}</div>
            </div>
            """
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def _safe_json_default(obj):
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def _render_results(result: dict) -> None:
    origin = result["origin"]
    destination = result["destination"]
    route = result["route"]
    roadwork_hits = result["roadwork_hits"]
    analyses = result["analyses"]
    best = result["best"]
    ai_report = result["ai_report"]
    travel_date = result["travel_date"]
    vehicle_type = result["vehicle_type"]
    driver_experience = result["driver_experience"]
    csv_path = result["csv_path"]
    sheet_name = result["sheet_name"]
    export_payload = result["export_payload"]

    st.success("Analiz tamamlandı. Sonuçlar aşağıda gösteriliyor.")

    top1, top2, top3, top4 = st.columns(4)
    with top1:
        st.metric("En uygun çıkış", best["hour"])
    with top2:
        st.metric("Risk skoru", f"{best['risk'].score:.1f}/100", best["risk"].category)
    with top3:
        st.metric("Mesafe", f"{route.distance_km:.0f} km")
    with top4:
        st.metric("Süre", f"{route.duration_min/60:.1f} saat")

    st.subheader("Çıkış saati karşılaştırması")
    table_rows = []
    for item in sorted(analyses, key=lambda x: x["hour"]):
        table_rows.append({
            "Saat": item["hour"],
            "Risk": item["risk"].score,
            "Kategori": item["risk"].category,
            "Hava": item["weather"].description,
            "Sıcaklık": f"{item['weather'].temperature_c:.1f}°C",
            "Yağış olasılığı": f"%{item['weather'].precipitation_probability:.0f}",
            "Güneş riski": item["sun"].label,
            "Güneş açısı": f"fark {item['sun'].angular_difference_deg:.0f}°, yükseklik {item['sun'].elevation_deg:.0f}°",
            "Tahmini maliyet": f"{item['expenses'].total_cost:,.0f} TL",
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    st.subheader("En iyi seçeneğin risk bileşenleri")
    comp_df = pd.DataFrame(
        [{"Bileşen": k, "Skora katkı": round(float(v), 1)} for k, v in best["risk"].components.items()]
    ).sort_values("Skora katkı", ascending=False)
    _render_component_bars(best["risk"].components)
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

    st.markdown(
        f"""
        <div class="card">
        <h3>Karar Özeti</h3>
        <p><b>Risk:</b> <span class="{_category_class(best['risk'].score)}">{best['risk'].score:.1f}/100 — {best['risk'].category}</span></p>
        <p><b>Öneri:</b> {best['risk'].recommendation}</p>
        <p class="small-note">Rota genel yönü: {route.start_bearing:.0f}° | Güneş değerlendirmesi: {best['sun'].label}, açı farkı {best['sun'].angular_difference_deg:.0f}°, güneş yüksekliği {best['sun'].elevation_deg:.0f}°.</p>
        <p class="small-note">Rota sağlayıcısı: {route.raw_provider}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_left, c_right = st.columns([1.2, 1])
    with c_left:
        st.subheader("Harita")
        if FOLIUM_AVAILABLE:
            center = route.midpoint
            fmap = folium.Map(location=[center[0], center[1]], zoom_start=6)
            folium.Marker([origin.lat, origin.lon], tooltip="Başlangıç", icon=folium.Icon(color="green")).add_to(fmap)
            folium.Marker([destination.lat, destination.lon], tooltip="Varış", icon=folium.Icon(color="red")).add_to(fmap)
            folium.PolyLine(route.geometry, tooltip="Rota").add_to(fmap)
            # returned_objects=[]: Harita bileşeninin gereksiz otomatik rerun üretmesini azaltır.
            try:
                st_folium(fmap, width=None, height=450, returned_objects=[])
            except TypeError:
                st_folium(fmap, width=None, height=450)
        else:
            st.info("Harita için streamlit-folium kurulmalıdır.")
    with c_right:
        st.subheader("Başlıca risk gerekçeleri")
        if best["risk"].reasons:
            for reason in best["risk"].reasons:
                st.write(f"- {reason}")
        else:
            st.write("Belirgin risk gerekçesi saptanmadı.")

        st.subheader("Demo yol çalışması kontrolü")
        if roadwork_hits:
            for hit in roadwork_hits[:5]:
                st.write(f"- **{hit.name}**: rotaya yaklaşık {hit.distance_to_route_km} km, seviye: {hit.severity}. {hit.note}")
        else:
            st.write("Demo veri setinde rotaya yakın yol çalışması görünmüyor.")

    st.subheader("Yapay zekâ yolculuk raporu")
    st.markdown(ai_report)

    st.subheader("Yanına alınacaklar listesi")
    for idx, item in enumerate(best["checklist"]):
        st.checkbox(item, value=False, key=f"checklist_{idx}_{best['hour']}")

    st.subheader("Masraf tahmini")
    exp = best["expenses"]
    exp_cols = st.columns(4)
    exp_cols[0].metric("Yakıt/enerji", f"{exp.fuel_cost:,.0f} TL")
    exp_cols[1].metric("Konaklama", f"{exp.accommodation_cost:,.0f} TL")
    exp_cols[2].metric("Yemek/ara ihtiyaç", f"{exp.food_cost:,.0f} TL")
    exp_cols[3].metric("Toplam", f"{exp.total_cost:,.0f} TL")
    for note in exp.notes:
        st.caption(note)

    st.subheader("Kayıt / dışa aktarma")
    st.write(f"Yerel CSV kayıt dosyası: `{csv_path}`")
    if sheet_name:
        st.success(f"Google Sheets'e de kaydedildi: {sheet_name}")
    else:
        st.caption("Google Sheets ayarlanmadığı için yalnızca yerel CSV kaydı yapıldı.")

    st.download_button(
        "Analizi JSON indir",
        data=json.dumps(export_payload, ensure_ascii=False, indent=2, default=_safe_json_default),
        file_name="yolguard_ai_analiz.json",
        mime="application/json",
        use_container_width=True,
        key="download_analysis_json",
    )

    st.caption(f"Son analiz: {origin.query} → {destination.query} | {travel_date} | {vehicle_type} | {driver_experience}")


def _run_analysis(
    origin_query: str,
    destination_query: str,
    travel_date: date,
    selected_hours: list[str],
    vehicle_type: str,
    driver_experience: str,
    timezone: str,
    passenger_count: int,
    max_daily_drive_hours: float,
    has_baby: bool,
    has_child: bool,
    has_pet: bool,
    accommodation_needed: bool,
    fuel_price: float,
    consumption: float,
    hotel_price: float,
    rooms: int,
    meal_budget: float,
    ev_range: float | None,
) -> dict:
    with st.status("Yolculuk verileri toplanıyor ve risk skoru hesaplanıyor...", expanded=True) as status:
        st.write("Adresler koordinata çevriliyor...")
        origin = geocode_address(origin_query)
        destination = geocode_address(destination_query)

        st.write("Rota hesaplanıyor...")
        route = fetch_route(origin, destination)
        roadwork_hits = find_nearby_roadworks(route.geometry)

        profile = TravelProfile(
            vehicle_type=vehicle_type,
            driver_experience=driver_experience,
            passenger_count=int(passenger_count),
            has_baby=has_baby,
            has_child=has_child,
            has_pet=has_pet,
            max_daily_drive_hours=float(max_daily_drive_hours),
            ev_range_km=float(ev_range) if ev_range else None,
        )

        analyses = []
        for hour_label in selected_hours:
            dt = datetime.combine(travel_date, _parse_time_label(hour_label))
            st.write(f"{hour_label} çıkışı için hava, güneş ve risk hesaplanıyor...")
            weather = fetch_weather(route.midpoint[0], route.midpoint[1], dt, timezone)
            sun_glare = calculate_sun_glare(route.midpoint[0], route.midpoint[1], route.start_bearing, dt, timezone)
            risk = calculate_risk(profile, route, weather, sun_glare, dt)
            expenses = estimate_expenses(
                distance_km=route.distance_km,
                passenger_count=int(passenger_count),
                vehicle_type=vehicle_type,
                fuel_price_try=float(fuel_price),
                consumption_per_100km=float(consumption),
                accommodation_needed=accommodation_needed,
                hotel_price_per_room=float(hotel_price),
                rooms=int(rooms),
                meal_budget_per_person=float(meal_budget),
            )
            checklist = build_checklist(profile, risk, weather, route)
            analyses.append({
                "hour": hour_label,
                "datetime": dt,
                "weather": weather,
                "sun": sun_glare,
                "risk": risk,
                "expenses": expenses,
                "checklist": checklist,
            })

        analyses.sort(key=lambda x: x["risk"].score)
        best = analyses[0]
        st.write("Yapay zekâ yolculuk raporu hazırlanıyor...")
        ai_report = generate_ai_advice(
            origin=origin.display_name,
            destination=destination.display_name,
            departure_label=f"{travel_date.isoformat()} {best['hour']}",
            risk=best["risk"],
            profile=profile,
            route=route,
            weather=best["weather"],
            sun_glare=best["sun"],
            checklist=best["checklist"],
            expenses=best["expenses"],
        )
        status.update(label="Analiz tamamlandı", state="complete")

    exp = best["expenses"]
    log_row = {
        "origin": origin.query,
        "destination": destination.query,
        "date": travel_date.isoformat(),
        "best_hour": best["hour"],
        "vehicle_type": vehicle_type,
        "driver_experience": driver_experience,
        "distance_km": route.distance_km,
        "duration_min": route.duration_min,
        "risk_score": best["risk"].score,
        "risk_category": best["risk"].category,
        "weather": best["weather"].description,
        "sun_glare": best["sun"].label,
        "total_cost": exp.total_cost,
        "components": best["risk"].components,
        "reasons": best["risk"].reasons,
    }
    csv_path = log_to_csv(log_row)
    sheet_name = log_to_google_sheets(log_row)

    export_payload = {
        **log_row,
        "ai_report": ai_report,
        "checklist": best["checklist"],
    }

    return {
        "origin": origin,
        "destination": destination,
        "route": route,
        "roadwork_hits": roadwork_hits,
        "profile": profile,
        "analyses": analyses,
        "best": best,
        "ai_report": ai_report,
        "travel_date": travel_date,
        "vehicle_type": vehicle_type,
        "driver_experience": driver_experience,
        "csv_path": csv_path,
        "sheet_name": sheet_name,
        "export_payload": export_payload,
    }


with st.form("trip_form"):
    st.subheader("1) Yolculuk bilgilerini girin")
    c1, c2 = st.columns(2)
    with c1:
        origin_query = st.text_input("Başlangıç adresi", value="Gebze, Kocaeli")
        travel_date = st.date_input("Yolculuk tarihi", value=date.today())
        vehicle_type = st.selectbox("Araç tipi", VEHICLES, index=1)
        driver_experience = st.selectbox("Sürücü tecrübesi", EXPERIENCE, index=0)
        timezone = st.text_input("Saat dilimi", value="Europe/Istanbul")
    with c2:
        destination_query = st.text_input("Varış adresi", value="Ağrı Merkez")
        selected_hours = st.multiselect("Karşılaştırılacak çıkış saatleri", DEFAULT_HOURS, default=["08:00", "10:00", "12:00", "16:00"])
        passenger_count = st.number_input(
            "Toplam kişi sayısı (sürücü dahil)",
            min_value=1,
            max_value=9,
            value=1,
            help="Demo güvenlik varsayımı: motosiklet en fazla 2, otomobil/elektrikli otomobil en fazla 5 kişi kabul edilir. Aşım olursa risk çok yükseltilir."
        )
        capacity_note = vehicle_capacity(vehicle_type)
        if int(passenger_count) > capacity_note:
            st.warning(f"Seçilen araç tipi için demo kapasite aşımı var: {int(passenger_count)}/{capacity_note}. Risk skoru çok yüksek hesaplanacaktır.")
        max_daily_drive_hours = st.slider("Kişisel günlük sürüş limiti", min_value=2.0, max_value=12.0, value=6.0, step=0.5)

    st.subheader("2) Ek durumlar")
    e1, e2, e3, e4 = st.columns(4)
    with e1:
        has_baby = st.checkbox("Bebek var")
    with e2:
        has_child = st.checkbox("Çocuk var")
    with e3:
        has_pet = st.checkbox("Evcil hayvan var")
    with e4:
        accommodation_needed = st.checkbox("Konaklama planlanacak")

    st.subheader("3) Masraf varsayımları")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        fuel_price = st.number_input("Yakıt/enerji birim fiyatı", min_value=0.0, value=45.0, step=1.0, help="Benzin için TL/L, elektrikli araç için TL/kWh kabul edilir.")
    with m2:
        consumption = st.number_input("Tüketim / 100 km", min_value=0.0, value=3.5 if vehicle_type == "Motosiklet" else 7.0, step=0.1, help="Benzin için L/100 km, elektrikli araç için kWh/100 km.")
    with m3:
        hotel_price = st.number_input("Oda fiyatı", min_value=0.0, value=1800.0, step=100.0)
    with m4:
        rooms = st.number_input("Oda sayısı", min_value=1, max_value=5, value=1)
    meal_budget = st.number_input("Kişi başı yemek/ara ihtiyaç bütçesi", min_value=0.0, value=350.0, step=50.0)

    ev_range = None
    if vehicle_type == "Elektrikli otomobil":
        ev_range = st.number_input("Elektrikli araç tahmini menzili (km)", min_value=50.0, value=350.0, step=10.0)

    submitted = st.form_submit_button("Yolculuğu analiz et", use_container_width=True)


if submitted:
    if not selected_hours:
        st.error("En az bir çıkış saati seçmelisiniz.")
    else:
        try:
            st.session_state["analysis_result"] = _run_analysis(
                origin_query=origin_query,
                destination_query=destination_query,
                travel_date=travel_date,
                selected_hours=selected_hours,
                vehicle_type=vehicle_type,
                driver_experience=driver_experience,
                timezone=timezone,
                passenger_count=int(passenger_count),
                max_daily_drive_hours=float(max_daily_drive_hours),
                has_baby=has_baby,
                has_child=has_child,
                has_pet=has_pet,
                accommodation_needed=accommodation_needed,
                fuel_price=float(fuel_price),
                consumption=float(consumption),
                hotel_price=float(hotel_price),
                rooms=int(rooms),
                meal_budget=float(meal_budget),
                ev_range=float(ev_range) if ev_range else None,
            )
        except GeocodingError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.exception(exc)


if st.session_state.get("analysis_result"):
    _render_results(st.session_state["analysis_result"])
else:
    st.info("Sol ve orta alandaki formu doldurup **Yolculuğu analiz et** butonuna basın.")

    st.subheader("Projenin kısa amacı")
    st.write(
        "YolGuard AI; rota, hava durumu, güneş kamaşması, araç tipi, sürücü tecrübesi ve yolcu özel durumlarını birlikte değerlendirerek yolculuk öncesi risk skoru ve hazırlık tavsiyesi üretir."
    )
