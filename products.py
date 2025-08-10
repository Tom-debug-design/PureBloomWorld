# products.py
from dataclasses import dataclass, asdict
from typing import List

@dataclass
class Product:
    id: str
    title: str
    image: str
    url: str           # affiliate-url (kan mangle for nå)
    price: float | None = None
    score: float = 0.0 # bruk til rangering

# TODO: erstatt med faktiske bestselgere + dine affiliate-lenker
PRODUCT_DB: List[Product] = [
    Product(id="amz-echo-dot", title="Echo Dot (5th gen)",
            image="https://m.media-amazon.com/images/I/71j8b1EOKXL._AC_SL1500_.jpg",
            url="https://www.amazon.com/dp/B09B2SB8QK", price=49.99, score=9.3),
    Product(id="amz-airfryer", title="COSORI Air Fryer Pro II",
            image="https://m.media-amazon.com/images/I/71bwy2+P2HL._AC_SL1500_.jpg",
            url="https://www.amazon.com/dp/B07Q2VFX3L", price=119.99, score=8.9),
    Product(id="amz-anker-charger", title="Anker 20W USB-C Charger",
            image="https://m.media-amazon.com/images/I/61j17F3L2fL._AC_SL1500_.jpg",
            url="https://www.amazon.com/dp/B08L8L9TCZ", price=16.99, score=8.7),
]

def get_top_sellers(n: int = 5) -> list[dict]:
    items = sorted(PRODUCT_DB, key=lambda p: p.score, reverse=True)[:n]
    return [asdict(p) for p in items]

def get_product(pid: str) -> Product | None:
    return next((p for p in PRODUCT_DB if p.id == pid), None)