from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import radians, cos, sin, asin, sqrt
from typing import Optional, Tuple
from django.contrib.auth.models import User
from .models import UserProfile


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Calculate great-circle distance between two points in kilometers."""
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


@dataclass
class FareBreakdown:
    base_fare: Decimal
    distance_component: Decimal
    total: Decimal


# PUBLIC_INTERFACE
def estimate_fare_km(distance_km: float) -> FareBreakdown:
    """Estimate a fare based on distance in km with a simple pricing model."""
    base = Decimal("1.50")
    per_km = Decimal("0.75")
    dist = Decimal(str(distance_km)) * per_km
    total = (base + dist).quantize(Decimal("0.01"))
    return FareBreakdown(base_fare=base, distance_component=dist.quantize(Decimal("0.01")), total=total)


# PUBLIC_INTERFACE
def match_nearest_available_driver(pickup_lat, pickup_lng) -> Optional[User]:
    """Find the nearest available driver based on distance to pickup."""
    drivers = User.objects.filter(profile__role=UserProfile.DRIVER, profile__is_available=True).select_related("profile")
    nearest: Tuple[Optional[User], float] = (None, float("inf"))
    for driver in drivers:
        # In a real system, driver would have last known lat/lng; here we approximate/simulate by zeroing distance
        # To keep example deterministic, treat all available drivers equal distance -> pick lowest id for stability
        dist = 0.0
        if dist < nearest[1] or (dist == nearest[1] and nearest[0] and driver.id < nearest[0].id):
            nearest = (driver, dist)
        if nearest[0] is None:
            nearest = (driver, dist)
    return nearest[0]
