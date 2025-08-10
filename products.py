# products.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import os
import asyncio

# Kilde/marketplace for visning i meldinger
SOURCE_NAME = os.getenv("PRODUCT_SOURCE", "amazon")

# TODO: Når du får affiliate-tag (f.eks. tag=xxx), sett den her:
AFFIL_TAG = os.getenv("AFFIL_TAG", "").strip()

def with_affiliate(url: str) -> str:
    """
    Legg til affiliate-tag senere. Nå returnerer vi bare url uendret.
    Eksempel for Amazon senere:
    - hvis '?tag=' ikke finnes -> append '?tag=AFFIL_TAG'
    """
    if not AFFIL_TAG:
        return url
    # plassholder – implementeres når vi har konkrete partnere
    return url

@dataclass
class Product:
    id: str
    title: str
    image: str
    url: str              # merchant-url (vi kan bytte til affiliate senere)
    price: Optional[float] = None
    score: float = 0.0    # enkel ranking-score

    def to_public(self) -> Dict:
        d = asdict(self)
        d["source"] = SOURCE_NAME
        d["url"] = with_affiliate(self.url)
        return d

# Dummy DB (bytt ut med faktiske bestselgere og affiliate-lenker)
PRODUCT_DB: List[Product] = [
    Product(
        id="amz-echo-dot",
        title="Echo Dot (5th gen)",
        image="https://m.media-amazon.com/images/I/71j8b1E0KXL._AC_SL1500_.jpg",
        url="https://www.amazon.com/dp/B09B2SB8QK",
        price=49.99,
        score=9.3,
    ),
    Product(
        id="amz-airfryer",
        title="COSORI Air Fryer Pro II",
        image="https://m.media-amazon.com/images/I/71bwy2+P2HL._AC_SL1500_.jpg",
        url="https://www.amazon.com/dp/B07Q2VFX3L",
        price=119.99,
        score=8.9,
    ),
    Product(
        id="amz-anker-pb",
        title="Anker Power Bank 20,000mAh",
        image="https://m.media-amazon.com/images/I/61l1kF8b-PL._AC_SL1500_.jpg",
        url="https://www.amazon.com/dp/B0B7QJZ1WZ",
        price=39.99,
        score=8.5,
    ),
    Product(
        id="amz-apple-airpods2",
        title="Apple AirPods (2nd Gen)",
        image="https://m.media-amazon.com/images/I/61yXc9q6EdL._AC_SL1500_.jpg",
        url="https://www.amazon.com/dp/B0BDHWDR12",
        price=99.00,
        score=9.1,
    ),
    Product(
        id="amz-fire-tv",
        title="Fire TV Stick 4K",
        image="https://m.media-amazon.com/images/I/71vD5o9u8dL._AC_SL1500_.jpg",
        url="https://www.amazon.com/dp/B08XVYZ1Y5",
        price=34.99,
        score=8.7,
    ),
    Product(
        id="amz-hydroflask",
        title="Hydro Flask 32oz",
        image="https://m.media-amazon.com/images/I/51pQf8qk5hL._AC_SL1500_.jpg",
        url="https://www.amazon.com/dp/B07TB3Z9S4",
        price=44.95,
        score=8.2,
    ),
]

def _rank_key(p: Product):
    # Enkel ranking: høy score først, deretter lavere pris
    # (kan byttes til salgstall/klikk senere)
    return (-p.score, p.price if p.price is not None else 1e9, p.title.lower())

async def get_top_sellers(limit: int = 10) -> List[Dict]:
    """
    Returnerer en liste med dicts for topp-produkter.
    Asynk for å matche kallene i main.py, selv om vi bruker in‑memory DB nå.
    """
    # Simuler evt. IO hvis vi senere henter fra API
    await asyncio.sleep(0)
    items = sorted(PRODUCT_DB, key=_rank_key)[:limit]
    return [p.to_public() for p in items]