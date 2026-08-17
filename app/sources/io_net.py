"""app/sources/io_net.py — io.net adapter ($100 GPU trial)."""
from __future__ import annotations
import json, re, urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "io-net"
CADENCE_MINUTES = 1440
URL = "https://io.net"

def fetch():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "deal-radar/2.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode("utf-8", errors="replace")
        return [Observation(source_id=SOURCE_ID, source_type="provider_page", url=URL,
                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="provider_page", url=URL,
                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)))]

def extract(observation):
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []
    if re.search(r'\$100|free.*trial|trial.*credit', text, re.IGNORECASE):
        offers.append(OfferSnapshot(
            provider_id="io-net", model_id="io-net/gpu-trial",
            provider_model_slug="gpu-trial", offer_kind="signup_credit",
            credits_included=100.0,
            metadata={"source_url": URL, "credit_type": "gpu_trial", "automation_allowed": False}))
    return offers
