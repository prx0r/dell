"""app/sources/artificial_analysis.py — Artificial Analysis adapter (v2 API).

Uses the official AA Data API v2 with proper rate limiting.

Rate limits (Free tier):
- 100 requests per FIXED 24h window (not rolling)
- Window resets when 24h elapsed after first request
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- On 429: check Retry-After header

We use 2 calls per poll (paginated), so ~48 calls/day max.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from . import Observation, OfferSnapshot, sha256, now_iso

# Load .env if present
_env = Path(__file__).resolve().parents[2] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


SOURCE_ID = "artificial-analysis"
CADENCE_MINUTES = 1440  # 24h

BASE_URL = "https://artificialanalysis.ai/api/v2"
FREE_ENDPOINT = "/language/models/free"
DOCS_URL = "https://artificialanalysis.ai/data-api/docs"

# Rate limit state (persisted to disk)
RATE_LIMIT_FILE = Path(__file__).resolve().parents[1] / "data" / "aa_rate_limit.json"


def _load_rate_limit() -> dict:
    if RATE_LIMIT_FILE.exists():
        try:
            return json.loads(RATE_LIMIT_FILE.read_text())
        except Exception:
            pass
    return {"requests_today": 0, "window_start": 0, "remaining": 100}


def _save_rate_limit(state: dict):
    RATE_LIMIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RATE_LIMIT_FILE.write_text(json.dumps(state))


def _check_rate_limit() -> bool:
    """Check if we're within rate limits. Returns True if OK to proceed."""
    state = _load_rate_limit()
    now = time.time()
    window = 86400  # 24h

    # Check if window has expired
    if now - state["window_start"] > window:
        # New window
        state = {"requests_today": 0, "window_start": now, "remaining": 100}
        _save_rate_limit(state)
        return True

    # Check remaining
    if state["remaining"] <= 0:
        reset_at = state["window_start"] + window
        wait_sec = reset_at - now
        if wait_sec > 0:
            print(f"  [AA] Rate limit exhausted. Resets in {wait_sec/3600:.1f}h")
            return False

    return True


def _record_request(headers: dict):
    """Record a request and update rate limit state from response headers."""
    state = _load_rate_limit()
    state["requests_today"] += 1

    # Update from response headers if available
    remaining = headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        try:
            state["remaining"] = int(remaining)
        except (ValueError, TypeError):
            state["remaining"] = max(0, state["remaining"] - 1)

    limit = headers.get("X-RateLimit-Limit")
    if limit is not None:
        try:
            state["limit"] = int(limit)
        except (ValueError, TypeError):
            pass

    _save_rate_limit(state)


def fetch() -> list[Observation]:
    """Fetch AA free-tier language models (paginated)."""
    api_key = os.environ.get("AA_API_KEY")
    if not api_key:
        return [Observation(
            source_id=SOURCE_ID, source_type="api_json",
            url=DOCS_URL, fetched_at=now_iso(), status=None,
            text="MISSING_KEY: AA_API_KEY not set. Get key at https://artificialanalysis.ai/api-key-management-redirect",
            sha256=sha256("missing_key"),
            metadata={"docs": DOCS_URL, "rate_limit": "Free: 100 req/24h"},
        )]

    if not _check_rate_limit():
        return [Observation(
            source_id=SOURCE_ID, source_type="api_json",
            url=BASE_URL + FREE_ENDPOINT, fetched_at=now_iso(), status=None,
            text="RATE_LIMITED: Daily quota exhausted",
            sha256=sha256("rate_limited"),
        )]

    observations = []
    page = 1
    while True:
        url = f"{BASE_URL}{FREE_ENDPOINT}?page={page}"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0",
                "x-api-key": api_key,
                "Accept": "application/json",
            })
            resp = urllib.request.urlopen(req, timeout=30)
            text = resp.read().decode("utf-8")
            _record_request(dict(resp.headers))

            observations.append(Observation(
                source_id=SOURCE_ID, source_type="api_json",
                url=url, fetched_at=now_iso(), status=resp.status,
                text=text, sha256=sha256(text),
                metadata={"page": page, "docs": DOCS_URL},
            ))

            # Check pagination
            data = json.loads(text)
            pagination = data.get("pagination", {})
            if not pagination.get("has_more", False):
                break
            page += 1
            if page > 10:  # safety limit
                break

        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After", "unknown")
                print(f"  [AA] Rate limited (429). Retry-After: {retry_after}s")
                observations.append(Observation(
                    source_id=SOURCE_ID, source_type="api_json",
                    url=url, fetched_at=now_iso(), status=429,
                    text=f"RATE_LIMITED: 429 Too Many Requests. Retry-After: {retry_after}",
                    sha256=sha256(f"429_{retry_after}"),
                ))
                break
            elif e.code == 401:
                observations.append(Observation(
                    source_id=SOURCE_ID, source_type="api_json",
                    url=url, fetched_at=now_iso(), status=401,
                    text="AUTH_ERROR: Invalid API key",
                    sha256=sha256("401"),
                ))
                break
            elif e.code == 403:
                observations.append(Observation(
                    source_id=SOURCE_ID, source_type="api_json",
                    url=url, fetched_at=now_iso(), status=403,
                    text="FORBIDDEN: Tier does not cover this endpoint",
                    sha256=sha256("403"),
                ))
                break
            else:
                observations.append(Observation(
                    source_id=SOURCE_ID, source_type="api_json",
                    url=url, fetched_at=now_iso(), status=e.code,
                    text=f"FETCH_ERROR: HTTP {e.code}",
                    sha256=sha256(f"error_{e.code}"),
                ))
                break
        except Exception as e:
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="api_json",
                url=url, fetched_at=now_iso(), status=None,
                text=f"FETCH_ERROR: {e}",
                sha256=sha256(str(e)),
            ))
            break

    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    """Extract offer snapshots from AA response."""
    if observation.status is None or "FETCH_ERROR" in observation.text or "MISSING_KEY" in observation.text or "RATE_LIMITED" in observation.text:
        return []

    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []

    offers = []
    for m in data.get("data", []):
        if not isinstance(m, dict):
            continue

        slug = m.get("slug", "")
        creator = m.get("model_creator", {})
        creator_name = creator.get("name", "").lower().replace(" ", "")

        # Build model ID
        model_id = f"{creator_name}/{slug}" if creator_name and slug else slug
        if not model_id:
            continue

        # Pricing
        pricing = m.get("pricing", {})
        in_price = pricing.get("price_1m_input_tokens")
        out_price = pricing.get("price_1m_output_tokens")
        cache_hit = pricing.get("price_1m_cache_hit_tokens")

        # Evaluations
        evals = m.get("evaluations", {})
        intel_index = evals.get("artificial_analysis_intelligence_index")
        coding_index = evals.get("artificial_analysis_coding_index")
        agentic_index = evals.get("artificial_analysis_agentic_index")

        # Performance
        perf = m.get("performance", {})
        tps = perf.get("median_output_tokens_per_second")
        ttft = perf.get("median_time_to_first_token_seconds")

        # Context
        ctx = m.get("context_window_tokens")

        offers.append(OfferSnapshot(
            provider_id=creator_name or "unknown",
            model_id=model_id,
            provider_model_slug=slug,
            offer_kind="metered_api",
            input_per_m=in_price,
            output_per_m=out_price,
            cache_read_per_m=cache_hit,
            free=(in_price == 0 and out_price == 0) if in_price is not None and out_price is not None else False,
            context_tokens=ctx,
            metadata={
                "source_url": observation.url,
                "docs": DOCS_URL,
                "intelligence_index": intel_index,
                "coding_index": coding_index,
                "agentic_index": agentic_index,
                "throughput_tps": tps,
                "ttft_seconds": ttft,
                "release_date": m.get("release_date"),
                "attribution": "Data: Artificial Analysis (artificialanalysis.ai)",
            },
        ))

    return offers
