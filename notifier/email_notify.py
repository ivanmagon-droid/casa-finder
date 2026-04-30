"""
Notifier email per nuovi annunci Casa Finder BGY1.
Invia una email riepilogativa con i nuovi annunci trovati.
Uso: python notifier/email_notify.py  (legge data/new_listings.json)
Oppure importato da n8n via Execute Command.
"""
import os
import json
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", "ivan.magon@gmail.com")


def _badge_stato(stato: str) -> str:
    colori = {
        "nuovo": "#6c757d",
        "visto": "#0d6efd",
        "contattato": "#ffc107",
        "preferito": "#198754",
        "scartato": "#dc3545",
    }
    colore = colori.get(stato, "#6c757d")
    return f'<span style="background:{colore};color:white;padding:2px 8px;border-radius:4px;font-size:11px;">{stato.upper()}</span>'


def _card_html(a: Dict) -> str:
    foto_html = ""
    if a.get("foto"):
        foto_html = f'<img src="{a["foto"][0]}" style="width:100%;max-height:180px;object-fit:cover;border-radius:6px;margin-bottom:10px;" />'

    distanza = f"{a['distanza_km']:.1f} km" if a.get("distanza_km") else "N/D"
    superficie = f"{a['superficie_mq']} m²" if a.get("superficie_mq") else "N/D"
    locali = f"{a['locali']} loc." if a.get("locali") else "N/D"
    arredato = "✅ Arredato" if a.get("arredato") else ""

    return f"""
    <div style="background:#1e2a3a;border:1px solid #2d3f55;border-radius:10px;padding:16px;
                margin-bottom:16px;font-family:'Courier New',monospace;">
      {foto_html}
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
        <strong style="color:#e0e0e0;font-size:14px;">{a.get('titolo','Annuncio')}</strong>
        {_badge_stato(a.get('stato','nuovo'))}
      </div>
      <div style="color:#00d4ff;font-size:22px;font-weight:bold;margin-bottom:6px;">
        €{a.get('prezzo','N/D')}/mese
      </div>
      <div style="color:#a0b4c8;font-size:12px;margin-bottom:10px;">
        📍 {a.get('comune','N/D')} &nbsp;|&nbsp; 🚗 {distanza} &nbsp;|&nbsp; 📐 {superficie} &nbsp;|&nbsp; 🚪 {locali}
        {'&nbsp;|&nbsp; ' + arredato if arredato else ''}
      </div>
      <div style="margin-top:10px;">
        <a href="{a.get('url','#')}" style="background:#00d4ff;color:#0a0e1a;padding:6px 14px;
           border-radius:5px;text-decoration:none;font-size:12px;font-weight:bold;margin-right:8px;">
          🔗 Vedi annuncio
        </a>
        <a href="{a.get('url_facebook','#')}" style="background:#1877f2;color:white;padding:6px 14px;
           border-radius:5px;text-decoration:none;font-size:12px;font-weight:bold;">
          Facebook
        </a>
      </div>
    </div>
    """


def genera_html(annunci: List[Dict]) -> str:
    cards = "".join(_card_html(a) for a in annunci)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="background:#0a0e1a;color:#e0e0e0;font-family:Arial,sans-serif;padding:20px;margin:0;">
  <div style="max-width:600px;margin:0 auto;">
    <div style="background:#111827;border:1px solid #2d3f55;border-radius:12px;
                padding:20px;margin-bottom:20px;text-align:center;">
      <h1 style="color:#00d4ff;font-family:'Courier New',monospace;margin:0;font-size:22px;">
        🏠 Casa Finder BGY1
      </h1>
      <p style="color:#a0b4c8;margin:8px 0 0;font-size:13px;">
        {len(annunci)} nuov{'o' if len(annunci)==1 else 'i'} annunci trovati — {now}
      </p>
    </div>
    {cards}
    <p style="color:#4a5568;font-size:11px;text-align:center;margin-top:20px;">
      Casa Finder BGY1 · Aggiornamento automatico ogni ora · Cividate al Piano (BG) ±30km
    </p>
  </div>
</body>
</html>
"""


def invia_email(annunci: List[Dict]) -> bool:
    if not annunci:
        print("[notifier] Nessun nuovo annuncio, email non inviata.")
        return False
    if not EMAIL_FROM or not EMAIL_PASSWORD:
        print("[notifier] EMAIL_FROM o EMAIL_PASSWORD mancanti nel .env")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🏠 Casa Finder: {len(annunci)} nuov{'o' if len(annunci)==1 else 'i'} annunci"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    testo_plain = f"Trovati {len(annunci)} nuovi annunci:\n\n"
    for a in annunci:
        testo_plain += (
            f"• {a.get('titolo','N/D')} — {a.get('comune','N/D')}\n"
            f"  €{a.get('prezzo','N/D')}/mese | {a.get('distanza_km','?')} km\n"
            f"  {a.get('url','')}\n\n"
        )

    msg.attach(MIMEText(testo_plain, "plain"))
    msg.attach(MIMEText(genera_html(annunci), "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print(f"[notifier] Email inviata a {EMAIL_TO} con {len(annunci)} annunci")
        return True
    except Exception as e:
        print(f"[notifier] Errore invio email: {e}")
        return False


def main():
    new_path = ROOT / "data" / "new_listings.json"
    if not new_path.exists():
        print("[notifier] data/new_listings.json non trovato")
        return

    with open(new_path, "r", encoding="utf-8") as f:
        annunci = json.load(f)

    invia_email(annunci)


if __name__ == "__main__":
    main()
