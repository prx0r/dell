"""app/sources/rss.py — Generic RSS/Atom feed watcher."""
from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "rss-feeds"
CADENCE_MINUTES = 120

DEFAULT_FEEDS = [
    "https://openrouter.ai/blog/feed.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://vercel.com/atom",
    "https://blog.cloudflare.com/rss/",
    "https://github.com/mnfst/awesome-free-llm-apis/releases.atom",
    "https://groq.com/blog/rss/",
    "https://deepinfra.com/blog/rss.xml",
    "https://together.ai/blog/rss.xml",
]

DEAL_KEYWORDS = re.compile(
    r"(free|discount|%[\s]*off|promo|promotion|launch[\s]*pric|credits?|bonus|"
    r"[2-9]x[\s]*(?:usage|tokens?|quota)|limited[\s]*time|until|through|extended|"
    r"off[\s]*peak|price[\s]*cut|price[\s]*drop|ends?\s*(?:in|on|at))", re.IGNORECASE)


def fetch(feeds: list[str] | None = None) -> list[Observation]:
    observations = []
    for url in (feeds or DEFAULT_FEEDS):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "deal-radar/2.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            text = resp.read().decode("utf-8", errors="replace")
            observations.append(Observation(source_id=SOURCE_ID, source_type="rss",
                url=url, fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text)))
        except Exception as e:
            observations.append(Observation(source_id=SOURCE_ID, source_type="rss",
                url=url, fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e))))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    offers = []
    try:
        root = ET.fromstring(observation.text)
    except ET.ParseError:
        return []
    # RSS 2.0
    for item in root.iter("item"):
        title = (item.findtext("title") or "")
        desc = (item.findtext("description") or "")
        link = (item.findtext("link") or "")
        text = f"{title} {desc}"
        if DEAL_KEYWORDS.search(text):
            offers.append(OfferSnapshot(
                provider_id="community", model_id=None, provider_model_slug=None,
                offer_kind="community_lead",
                metadata={"source_url": link, "title": title, "excerpt": desc[:500],
                          "deal_keywords": DEAL_KEYWORDS.findall(text)}))
    # Atom
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = (entry.findtext("atom:title", namespaces=ns) or "")
        summary = (entry.findtext("atom:summary", namespaces=ns) or "")
        link_el = entry.find("atom:link", ns)
        link = link_el.get("href", "") if link_el is not None else ""
        text = f"{title} {summary}"
        if DEAL_KEYWORDS.search(text):
            offers.append(OfferSnapshot(
                provider_id="community", model_id=None, provider_model_slug=None,
                offer_kind="community_lead",
                metadata={"source_url": link, "title": title, "excerpt": summary[:500]}))
    return offers
