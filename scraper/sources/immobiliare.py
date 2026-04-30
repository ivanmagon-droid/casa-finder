"""
Scraper per Immobiliare.it via API pubblica.
"""
import time
import hashlib
import requests
from datetime import datetime
from typing import List, Dict, Optional

from scraper.utils.geo import distanza_da_centro, dentro_raggio

BASE_API = "https://api.immobiliare.it/search-backend/listings"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "it-IT,it;q=0.9",
    "Referer": "https://www.immobiliare.it/",
}

PAROLE_ESCLUSE = ["solo coppie", "no single", "studenti", "temporaneo"]


def _make_id(listing: dict) -> str:
    raw_id = listing.get("realEstate", {}).get("id") or listing.get("id", "")
    return f"imm_{raw_id}"


def _estrai_comune(indirizzo: str) -> str:
    """Estrae il comune dall'indirizzo."""
    if not indirizzo:
        return ""
    parti = indirizzo.split(",")
    if len(parti) >= 2:
        comune = parti[-2].strip()
        # Rimuove province tra parentesi tipo (BG)
        if "(" in comune:
            comune = comune[:comune.index("(")].strip()
        return comune
    return indirizzo.strip()


def _parse_listing(item: dict) -> Optional[Dict]:
    re = item.get("realEstate", {})
    properties = re.get("properties", [{}])
    prop = properties[0] if properties else {}

    # Coordinate
    location = prop.get("location", {})
    lat = location.get("latitude")
    lon = location.get("longitude")
    if not lat or not lon:
        return None

    lat, lon = float(lat), float(lon)
    if not dentro_raggio(lat, lon, 30):
        return None

    # Prezzo
    price_info = prop.get("price", {})
    prezzo = price_info.get("value")
    if prezzo is None:
        return None
    try:
        prezzo = int(float(str(prezzo).replace(",", ".")))
    except (ValueError, TypeError):
        return None

    if prezzo > 720:
        return None

    # Descrizione – check parole escluse
    titolo = re.get("title") or prop.get("typology", {}).get("name", "Annuncio")
    descrizione = prop.get("description", "") or ""
    for parola in PAROLE_ESCLUSE:
        if parola.lower() in descrizione.lower():
            return None

    # Indirizzo
    indirizzo_obj = location.get("address", {})
    via = indirizzo_obj.get("localityDescription") or indirizzo_obj.get("city", "")
    cap = indirizzo_obj.get("postalCode", "")
    city = indirizzo_obj.get("city", "")
    comune = city or _estrai_comune(via)
    indirizzo_completo = f"{via}, {city} (BG)" if via else city

    # Superficie e locali
    superficie = None
    for feat in prop.get("surface", {}).values() if isinstance(prop.get("surface"), dict) else []:
        try:
            superficie = int(feat)
            break
        except (ValueError, TypeError):
            pass
    if superficie is None:
        sup_raw = prop.get("surfaceValue")
        try:
            superficie = int(str(sup_raw).replace(" m²", "").replace(",", ".")) if sup_raw else None
        except (ValueError, TypeError):
            superficie = None

    locali_raw = prop.get("rooms")
    try:
        locali = int(locali_raw) if locali_raw else None
    except (ValueError, TypeError):
        locali = None

    piano_raw = prop.get("floor", {})
    piano = piano_raw.get("value") if isinstance(piano_raw, dict) else None

    arredato = "arredato" in descrizione.lower() or "arred" in titolo.lower()

    # URL — priorità: seo.url → url diretto → costruito da ID
    listing_id_raw = re.get("id") or item.get("id", "")
    url = re.get("seo", {}).get("url", "") or re.get("url", "") or ""
    if url and not url.startswith("http"):
        url = "https://www.immobiliare.it" + url
    if not url and listing_id_raw:
        url = f"https://www.immobiliare.it/annunci/{listing_id_raw}/"

    # Foto
    foto = []
    for multimedia in re.get("multimedia", {}).get("photos", []):
        src = multimedia.get("urls", {}).get("large") or multimedia.get("urls", {}).get("medium", "")
        if src:
            foto.append(src)

    distanza = distanza_da_centro(lat, lon)

    # Facebook link
    fb_query = f"appartamento affitto {comune}".replace(" ", "%20")
    url_facebook = f"https://www.facebook.com/marketplace/search/?query={fb_query}&category_id=propertyrentals"

    return {
        "id": _make_id(item),
        "source": "immobiliare",
        "titolo": titolo,
        "prezzo": prezzo,
        "indirizzo": indirizzo_completo,
        "comune": comune,
        "lat": lat,
        "lon": lon,
        "distanza_km": distanza,
        "superficie_mq": superficie,
        "locali": locali,
        "piano": piano,
        "arredato": arredato,
        "url": url,
        "url_facebook": url_facebook,
        "foto": foto[:5],
        "descrizione": descrizione[:500],
        "telefono": "",
        "data_trovato": datetime.now().isoformat(),
        "data_pubblicazione": item.get("creationDate", "")[:10] if item.get("creationDate") else "",
        "stato": "nuovo",
        "note": "",
    }


def scrape(prezzo_max: int = 720, raggio_km: int = 30, max_pages: int = 5) -> List[Dict]:
    """Scarica annunci da Immobiliare.it. Ritorna lista di listing normalizzati."""
    results = []
    page = 1

    while page <= max_pages:
        params = {
            "fkRegione": "lombardia",
            "idNazione": "IT",
            "idContratto": 1,       # affitto
            "idCategoria": 1,       # residenziale
            "prezzoMassimo": prezzo_max,
            "raggio": raggio_km,
            "lat": 45.5947,
            "lng": 9.8367,
            "pag": page,
            "count": 25,
        }
        try:
            resp = requests.get(BASE_API, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[immobiliare] Errore pagina {page}: {e}")
            break

        items = data.get("results", [])
        if not items:
            break

        for item in items:
            parsed = _parse_listing(item)
            if parsed:
                results.append(parsed)

        total_pages = data.get("maxPages", 1)
        if page >= total_pages:
            break

        page += 1
        time.sleep(2.5)  # rispetta robots.txt

    print(f"[immobiliare] Trovati {len(results)} annunci validi")
    return results
