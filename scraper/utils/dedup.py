"""
Deduplicazione annunci: chiave = source_id oppure comune+prezzo+superficie.
"""
import json
import os
from typing import List, Dict

LISTINGS_PATH = os.path.join(os.path.dirname(__file__), "../../data/listings.json")


def carica_listings() -> List[Dict]:
    path = os.path.abspath(LISTINGS_PATH)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def ids_esistenti(listings: List[Dict]) -> set:
    return {l["id"] for l in listings}


def chiave_contenuto(listing: Dict) -> str:
    """Chiave fuzzy basata su contenuto per evitare duplicati cross-source."""
    comune = (listing.get("comune") or "").lower().strip()
    prezzo = listing.get("prezzo") or 0
    superficie = listing.get("superficie_mq") or 0
    return f"{comune}_{prezzo}_{superficie}"


def chiavi_contenuto_esistenti(listings: List[Dict]) -> set:
    return {chiave_contenuto(l) for l in listings}


def filtra_nuovi(candidati: List[Dict], listings_esistenti: List[Dict]) -> List[Dict]:
    """Rimuove i candidati già presenti nel database (per ID o contenuto)."""
    ids = ids_esistenti(listings_esistenti)
    chiavi = chiavi_contenuto_esistenti(listings_esistenti)
    nuovi = []
    for c in candidati:
        if c["id"] in ids:
            continue
        if chiave_contenuto(c) in chiavi:
            continue
        nuovi.append(c)
    return nuovi


def salva_listings(listings: List[Dict]) -> None:
    path = os.path.abspath(LISTINGS_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)


def aggiungi_listings(nuovi: List[Dict]) -> int:
    """Aggiunge nuovi annunci al database. Restituisce il numero di aggiunti."""
    esistenti = carica_listings()
    da_aggiungere = filtra_nuovi(nuovi, esistenti)
    if da_aggiungere:
        esistenti.extend(da_aggiungere)
        salva_listings(esistenti)
    return len(da_aggiungere)
