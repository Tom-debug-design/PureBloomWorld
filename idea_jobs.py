# idea_jobs.py
"""
Daglig idé-dropper til Discord.
- Kjører 08:00 Europe/Oslo
- Sender 3 produktideer + 3 artikkelideer
- Manuell trigger håndteres i main.py (/trigger/ideas)
"""

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import random

OSLO = ZoneInfo("Europe/Oslo")

PRODUCT_TOPICS = [
    ("Health", "Magnesium glycinate sleep stack"),
    ("Health", "Vitamin D3 + K2 winter kit"),
    ("Lifestyle", "Minimalist wallet with AirTag slot"),
    ("Tech", "USB‑C travel power hub (GaN)"),
    ("Tech", "Bone‑conduction workout headphones"),
    ("Eco", "Refillable cleaning concentrate kit"),
    ("Eco", "Compostable kitchen bags — leak‑proof"),
]

ARTICLE_TOPICS = [
    ("Health", "Skincare actives: niacinamide vs. retinol"),
    ("Health", "Creatine for focus — not just for gym"),
    ("Lifestyle", "Sleep hygiene checklist that actually works"),
    ("Tech", "Best budget microphones for mobile creators"),
    ("Tech", "Password hygiene in 10 minutes"),
    ("Eco", "How to cut plastic without pain"),
]

def compose_idea_message() -> str:
    picks_p = random.sample(PRODUCT_TOPICS, k=3)
    picks_a = random.sample(ARTICLE_TOPICS, k=3)
    lines = ["💡 **Daily Ideas**",
             "### Products:"]
    for cat, title in picks_p:
        lines.append(f"• **{title}**  _#{cat.lower()}_")
    lines.append("")
    lines.append("### Articles:")
    for cat, title in picks_a:
        lines.append(f"• **{title}**  _#{cat.lower()}_")
    lines.append("")
    lines.append("_(Affiliate links placeholder: add when approved)_")
    return "\n".join(lines)

def seconds_until_next_8_oslo(now_utc: datetime | None = None) -> float:
    if not now_utc:
        now_utc = datetime.now(timezone.utc)
    now_oslo = now_utc.astimezone(OSLO)
    target = now_oslo.replace(hour=8, minute=0, second=0, microsecond=0)
    if now_oslo >= target:
        target = target + timedelta(days=1)
    # tilbake til UTC
    target_utc = target.astimezone(timezone.utc)
    return (target_utc - now_utc).total_seconds()

async def daily_ideas_scheduler(post_func):
    """post_func: async function(str) -> bool"""
    # første vent til 08:00 Oslo
    delay = seconds_until_next_8_oslo()
    await asyncio.sleep(max(1, delay))
    while True:
        try:
            msg = compose_idea_message()
            await post_func(msg)
        except Exception as e:
            print(f"[WARN] daily ideas error: {e}")
        # vent 24h
        await asyncio.sleep(24 * 60 * 60)