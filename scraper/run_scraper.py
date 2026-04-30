"""
Entrypoint principale dello scraper Casa Finder BGY1.
Esegue tutti i moduli, deduplicata e salva i nuovi annunci.
Scrive data/new_listings.json con i soli annunci NUOVI (per n8n/notifier).
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Aggiungi la root del progetto al path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper.sources import immobiliare, subito
from scraper.utils.dedup import carica_listings, filtra_nuovi, salva_listings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "logs" / "scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def main():
    log.info("=" * 60)
    log.info("Avvio scraper Casa Finder BGY1")
    log.info(f"Timestamp: {datetime.now().isoformat()}")
    log.info("=" * 60)

    # Crea cartelle necessarie
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)

    tutti_nuovi = []

    # --- Immobiliare.it ---
    try:
        log.info("Scraping Immobiliare.it...")
        risultati_imm = immobiliare.scrape(prezzo_max=720, raggio_km=30, max_pages=6)
        tutti_nuovi.extend(risultati_imm)
        log.info(f"Immobiliare.it: {len(risultati_imm)} annunci trovati")
    except Exception as e:
        log.error(f"Errore Immobiliare.it: {e}")

    # --- Subito.it ---
    try:
        log.info("Scraping Subito.it...")
        risultati_sub = subito.scrape(prezzo_max=720, max_pages=5)
        tutti_nuovi.extend(risultati_sub)
        log.info(f"Subito.it: {len(risultati_sub)} annunci trovati")
    except Exception as e:
        log.error(f"Errore Subito.it: {e}")

    log.info(f"Totale annunci recuperati (pre-dedup): {len(tutti_nuovi)}")

    # --- Deduplicazione ---
    esistenti = carica_listings()
    nuovi_filtrati = filtra_nuovi(tutti_nuovi, esistenti)
    log.info(f"Nuovi annunci dopo deduplicazione: {len(nuovi_filtrati)}")

    # --- Salva listings.json (append) ---
    if nuovi_filtrati:
        esistenti.extend(nuovi_filtrati)
        salva_listings(esistenti)
        log.info(f"Salvati {len(nuovi_filtrati)} nuovi annunci in data/listings.json")

    # --- Salva new_listings.json (solo per notifiche n8n) ---
    new_path = ROOT / "data" / "new_listings.json"
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(nuovi_filtrati, f, ensure_ascii=False, indent=2)
    log.info(f"Scritto data/new_listings.json con {len(nuovi_filtrati)} annunci")

    # --- Summary ---
    log.info("=" * 60)
    log.info(f"RISULTATO: {len(nuovi_filtrati)} NUOVI annunci trovati")
    log.info(f"Totale nel database: {len(esistenti)}")
    log.info("=" * 60)

    # Stampa su stdout per n8n (Execute Command node legge stdout)
    print(json.dumps({
        "nuovi": len(nuovi_filtrati),
        "totale": len(esistenti),
        "timestamp": datetime.now().isoformat(),
        "annunci": nuovi_filtrati,
    }))

    return nuovi_filtrati


if __name__ == "__main__":
    main()
