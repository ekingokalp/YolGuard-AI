from datetime import datetime

from modules.risk_model import TravelProfile, calculate_risk
from modules.routing import RouteSummary
from modules.weather import WeatherSnapshot
from modules.sun import SunGlare


def make_route(distance_km=100, duration_min=90):
    return RouteSummary(
        distance_km=distance_km,
        duration_min=duration_min,
        geometry=[(40.0, 29.0), (40.5, 30.0)],
        start_bearing=90.0,
        midpoint=(40.25, 29.5),
    )


def make_weather(code=0, precipitation=0, wind=10, gust=15, temp=20):
    return WeatherSnapshot(
        description="Test",
        weather_code=code,
        temperature_c=temp,
        precipitation_probability=precipitation,
        rain_mm=0,
        wind_speed_kmh=wind,
        wind_gusts_kmh=gust,
        visibility_m=10000,
    )


def make_profile(vehicle="Otomobil", experience="Deneyimli"):
    return TravelProfile(
        vehicle_type=vehicle,
        driver_experience=experience,
        passenger_count=1,
        has_baby=False,
        has_child=False,
        has_pet=False,
        max_daily_drive_hours=6,
    )


def test_low_risk_is_lower_than_bad_conditions():
    low = calculate_risk(
        make_profile(),
        make_route(),
        make_weather(),
        SunGlare(azimuth_deg=180, elevation_deg=50, angular_difference_deg=120, risk=0, label="Düşük"),
        datetime(2026, 6, 10, 10, 0),
    )
    high = calculate_risk(
        make_profile(vehicle="Motosiklet", experience="Acemi"),
        make_route(distance_km=700, duration_min=600),
        make_weather(code=65, precipitation=90, wind=40, gust=60, temp=2),
        SunGlare(azimuth_deg=90, elevation_deg=8, angular_difference_deg=5, risk=95, label="Yüksek"),
        datetime(2026, 6, 10, 5, 0),
    )
    assert high.score > low.score
    assert high.category in {"Yüksek", "Çok yüksek"}


def test_ev_range_risk_increases_score():
    route = make_route(distance_km=300, duration_min=240)
    normal = calculate_risk(
        make_profile(vehicle="Elektrikli otomobil"),
        route,
        make_weather(),
        SunGlare(0, 50, 100, 0, "Düşük"),
        datetime(2026, 6, 10, 12, 0),
    )
    profile_with_short_range = TravelProfile(
        vehicle_type="Elektrikli otomobil",
        driver_experience="Deneyimli",
        passenger_count=1,
        has_baby=False,
        has_child=False,
        has_pet=False,
        max_daily_drive_hours=6,
        ev_range_km=250,
    )
    short_range = calculate_risk(
        profile_with_short_range,
        route,
        make_weather(),
        SunGlare(0, 50, 100, 0, "Düşük"),
        datetime(2026, 6, 10, 12, 0),
    )
    assert short_range.score >= normal.score


def test_motorcycle_capacity_violation_forces_very_high_risk():
    profile = TravelProfile(
        vehicle_type="Motosiklet",
        driver_experience="Acemi",
        passenger_count=4,
        has_baby=True,
        has_child=True,
        has_pet=True,
        max_daily_drive_hours=6,
    )
    result = calculate_risk(
        profile,
        make_route(distance_km=200, duration_min=180),
        make_weather(),
        SunGlare(azimuth_deg=90, elevation_deg=8, angular_difference_deg=20, risk=80, label="Yüksek güneş kamaşması riski"),
        datetime(2026, 6, 10, 8, 0),
    )
    assert result.score >= 90
    assert result.category == "Çok yüksek"
    assert any("Kapasite" in reason or "kapasite" in reason for reason in result.reasons)


def test_long_rookie_motorcycle_route_is_not_low_risk():
    profile = TravelProfile(
        vehicle_type="Motosiklet",
        driver_experience="Acemi",
        passenger_count=1,
        has_baby=False,
        has_child=False,
        has_pet=False,
        max_daily_drive_hours=6,
    )
    result = calculate_risk(
        profile,
        make_route(distance_km=800, duration_min=720),
        make_weather(),
        SunGlare(azimuth_deg=180, elevation_deg=50, angular_difference_deg=120, risk=0, label="Düşük güneş kamaşması riski"),
        datetime(2026, 6, 10, 10, 0),
    )
    assert result.score >= 75
    assert result.category in {"Yüksek", "Çok yüksek"}
