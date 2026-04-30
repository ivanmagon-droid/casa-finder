"""
Scraper per Subito.it tramite API JSON pubblica.
"""
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional

from scraper.utils.geo import distanza_da_centro, dentro_raggio

BASE_API = "https://www.subito.it/hades/v1/search/items/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "it-IT,it;q=0.9",
    "Referer": "https://www.subito.it/",
}

PAROLE_ESCLUSE = ["solo coppie", "no single", "studenti", "temporaneo"]


def _parse_listing(item: dict) -> Optional[Dict]:
    try:
        urn = item.get("urn", "")
        listing_id = f"sub_{item.get('id', urn.split(':')[-1])}"

        # Prezzo
        features = {f["uri"].split("/")[-1]: f for f in item.get("features", [])}
        prezzo_feat = features.get("price", {})
        prezzo_values = prezzo_feat.get("values", [{}])
        prezzo = None
        if prezzo_values:
            try:
                prezzo = int(float(prezzo_values[0].get("key", "0")))
            except (ValueError, TypeError):
                return None
        if not prezzo or prezzo > 720:
            return None

        # Geo
        geo = item.get("geo", {})
        lat = geo.get("map", {}).get("latitude")
        lon = geo.get("map", {}).get("longitude")
        if not lat or not lon:
            return None
        lat, lon = float(lat), float(lon)
        if not dentro_raggio(lat, lon, 30):
            return None

        # Titolo e descrizione
        titolo = item.get("subject", "Annuncio")
        descrizione = item.get("body", "") or ""
        for parola in PAROLE_ESCLUSE:
            if parola.lower() in descrizione.lower() or parola.lower() in titolo.lower():
                return None

        # Indirizzo e comune
        location = geo.get("city", {})
        comune = location.get("short_name") or location.get("value", "")
        region_info = item.get("location", {})
        indirizzo = region_info.get("value", comune)

        # Superficie e locali
        superficie = None
        locali = None
        for f in item.get("features", []):
            label = f.get("label", "").lower()
            vals = f.get("values", [{}])
            val = vals[0].get("value", "") if vals else ""
            if "superficie" in label or "mq" in label:
                try:
                    superficie = int(str(val).replace("m²", "").replace(",", ".").strip())
                except (ValueError, TypeError):
                    pass
            elif "local" in label or "vani" in label or "camere" in label:
                try:
                    locali = int(val)
                except (ValueError, TypeError):
                    pass

        arredato_feat = features.get("furnished", {})
        arredato = bool(arredato_feat.get("values"))

        # URL — priorità: urls.default → urls.short → costruito da URN/ID
        urls = item.get("urls", {})
        url = urls.get("default", "") or urls.get("short", "") or urls.get("iphone", "") or ""
        if url and not url.startswith("http"):
            url = "https://www.subito.it" + url
        if not url:
            # Fallback: costruisce URL da URN o ID numerico
            raw_id = item.get("id", "") or urn.split(":")[-1]
            if raw_id:
                url = f"https://www.subito.it/annunci/immobili/{raw_id}.htm"

        # Foto
        foto = []
        for img in item.get("images", []):
            src = img.get("scale", [{}])
            for s in src:
                if s.get("size") == "big":
                    foto.append(s.get("uri", ""))
                    break

        # Telefono
        advertiser = item.get("advertiser", {})
        telefono = advertiser.get("phone", "")

        distanza = distanza_da_centro(lat, lon)

        fb_query = f"appartamento affitto {comune}".replace(" ", "%20")
        url_facebook = f"https://www.facebook.com/marketplace/search/?query={fb_query}&category_id=propertyrentals"

        data_pub_raw = item.get("date", "")
        try:
            data_pub = data_pub_raw[:10] if data_pub_raw else ""
        except Exception:
            data_pub = ""

        return {
            "id": listing_id,
            "source": "subito",
            "titolo": titolo,
            "prezzo": prezzo,
            "indirizzo": indirizzo,
            "comune": comune,
            "lat": lat,
            "lon": lon,
            "distanza_km": distanza,
            "superficie_mq": superficie,
            "locali": locali,
            "piano": None,
            "arredato": arredato,
            "url": url,
            "url_facebook": url_facebook,
            "foto": foto[:5],
            "descrizione": descrizione[:500],
            "telefono": telefono,
            "data_trovato": datetime.now().isoformat(),
            "data_pubblicazione": data_pub,
            "stato": "nuovo",
            "note": "",
        }
    except Exception as e:
        print(f"[subito] Errore parsing annuncio: {e}")
        return None


def scrape(prezzo_max: int = 720, max_pages: int = 5) -> List[Dict]:
    """Scarica annunci da Subito.it. Ritorna lista di listing normalizzati."""
    results = []

    for page in range(1, max_pages + 1):
        params = {
            "c": 8,           # categoria appartamenti in affitto
            "t": "s",         # tipo: affitto
            "ps": 0,
            "pe": prezzo_max,
            "lim": 30,
            "start": (page - 1) * 30,
            "shp": 1,
            "lat": 45.5947,
            "lon": 9.8367,
            "rad": 30,
            "sort": "datedesc",
        }
        try:
            resp = requests.get(BASE_API, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[subito] Errore pagina {page}: {e}")
            break

        items = data.get("ads", []) or data.get("items", [])
        if not items:
            break

        for item in items:
            parsed = _parse_listing(item)
            if parsed:
                results.append(parsed)

        if len(items) < 30:
            break

        time.sleep(3)

    print(f"[subito] Trovati {len(results)} annunci validi")
    return results
