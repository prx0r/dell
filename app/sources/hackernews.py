"""app/sources/hackernews.py — Hacker News Firebase API adapter."""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "hackernews"
CADENCE_MINUTES = 120
BASE_URL = "https://hacker-news.firebaseio.com/v0"
DEAL_KEYWORDS = re.compile(r"(llm|model|free|pricing|api|inference|deal|promo|credits?|token)", re.IGNORECASE)


def fetch() -> list[Observation]:
    observations = []
    for endpoint in ["topstories", "newstories", "beststories"]:
        try:
            req = urllib.request.Request(f"{BASE_URL}/{endpoint}.json", headers={"User-Agent": "deal-radar/2.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            ids = json.loads(resp.read().decode())
            # Fetch top 30 stories from each list
            items = []
            for story_id in ids[:15]:  # Top 15 only (was 30 — too slow)
                try:
                    sreq = urllib.request.Request(f"{BASE_URL}/item/{story_id}.json")
                    sresp = urllib.request.urlopen(sreq, timeout=5)
                    items.append(json.loads(sresp.read().decode()))
                except Exception:
                    continue
            observations.append(Observation(source_id=SOURCE_ID, source_type="api_json",
                url=f"{BASE_URL}/{endpoint}.json", fetched_at=now_iso(), status=resp.status,
                text=json.dumps(items), sha256=sha256(json.dumps(items))))
        except Exception as e:
            observations.append(Observation(source_id=SOURCE_ID, source_type="api_json",
                url=f"{BASE_URL}/{endpoint}.json", fetched_at=now_iso(), status=None,
                text=f"FETCH_ERROR: {e}", sha256=sha256(str(e))))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    try:
        items = json.loads(observation.text)
    except json.JSONDecodeError:
        return []
    offers = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "")
        text = f"{title} {item.get('text', '')}"
        if DEAL_KEYWORDS.search(text):
            score = item.get("score", 0)
            if score < 5:
                continue
            offers.append(OfferSnapshot(
                provider_id="community", model_id=None, provider_model_slug=None,
                offer_kind="community_lead",
                metadata={"source_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
                          "title": title, "score": score, "author": item.get("by", ""),
                          "hn_type": item.get("type", "")}))
    return offers
