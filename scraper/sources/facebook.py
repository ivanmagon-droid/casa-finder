"""
Generatore link Facebook Marketplace (no automazione login).
"""

COMUNI = [
    "Treviglio", "Romano di Lombardia", "Caravaggio", "Martinengo",
    "Calcio", "Pumenengo", "Ghisalba", "Cologno al Serio",
    "Antegnate", "Barbata", "Fontanella", "Cividate al Piano",
    "Verdello", "Urgnano", "Zanica", "Dalmine",
]


def genera_link(comune: str) -> str:
    query = f"appartamento affitto {comune}".replace(" ", "%20")
    return f"https://www.facebook.com/marketplace/search/?query={query}&category_id=propertyrentals"


def tutti_i_link() -> dict:
    return {comune: genera_link(comune) for comune in COMUNI}
