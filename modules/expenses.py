from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpenseEstimate:
    fuel_cost: float
    accommodation_cost: float
    food_cost: float
    total_cost: float
    notes: list[str]


def estimate_expenses(
    distance_km: float,
    passenger_count: int,
    vehicle_type: str,
    fuel_price_try: float,
    consumption_per_100km: float,
    accommodation_needed: bool,
    hotel_price_per_room: float,
    rooms: int,
    meal_budget_per_person: float,
) -> ExpenseEstimate:
    vehicle = vehicle_type.lower()
    notes: list[str] = []
    if "elektrikli" in vehicle:
        # Elektrikli araçta consumption_per_100km alanını kWh/100 km olarak yorumluyoruz.
        energy_cost = distance_km * consumption_per_100km / 100 * fuel_price_try
        fuel_cost = energy_cost
        notes.append("Elektrikli araç için tüketim kWh/100 km, birim fiyat TL/kWh kabul edildi.")
    else:
        fuel_cost = distance_km * consumption_per_100km / 100 * fuel_price_try
        notes.append("Yakıt maliyeti yaklaşık değerdir; trafik, yük ve sürüş tarzı sonucu değiştirebilir.")

    accommodation_cost = hotel_price_per_room * rooms if accommodation_needed else 0.0
    food_cost = max(1, passenger_count) * meal_budget_per_person
    total = fuel_cost + accommodation_cost + food_cost
    return ExpenseEstimate(
        fuel_cost=round(fuel_cost, 2),
        accommodation_cost=round(accommodation_cost, 2),
        food_cost=round(food_cost, 2),
        total_cost=round(total, 2),
        notes=notes,
    )
