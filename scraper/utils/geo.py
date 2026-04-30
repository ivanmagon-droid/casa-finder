"""
Calcolo distanza da Cividate al Piano (BG).
"""
from geopy.distance import geodesic

CENTER_LAT = 45.5947
CENTER_LON = 9.8367
CENTER = (CENTER_LAT, CENTER_LON)


def distanza_da_centro(lat: float, lon: float) -> float:
    """Restituisce la distanza in km da Cividate al Piano."""
    punto = (lat, lon)
    return round(geodesic(CENTER, punto).km, 2)


def dentro_raggio(lat: float, lon: float, raggio_km: float = 30.0) -> bool:
    """Verifica se un punto è nel raggio specificato da Cividate al Piano."""
    return distanza_da_centro(lat, lon) <= raggio_km
