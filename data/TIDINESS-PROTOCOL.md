# Tidiness Protocol — Keeping the System Clean

## Problem: 2463 offers, 0 have expiry dates

This means we can't answer: "When does this deal end?"
The system looks comprehensive but can't do the most basic thing.

## Solution: Extract dates from source pages

### How to find expiry dates

**Source page patterns to look for:**

1. **Explicit dates**: "Expires December 31, 2026"
2. **Relative dates**: "30 days from signup"
3. **Rolling quotas**: "1,500 requests per 5 hours"
4. **Windowed quotas**: "per month", "per day"
5. **Limited time**: "limited time offer" (no date)
6. **Promo periods**: "launch pricing through August"

**What we should store:**

```json
{
  "expires_at": "2026-12-31T23:59:59Z",  // if known
  "expiry_precision": "day",              // day/hour/minute/unknown
  "expiry_timezone": "UTC",               // if known
  "expiry_basis": "explicit",             // explicit/relative/rolling/unknown
  "quota_window": "5 hours",              // for rolling quotas
  "quota_amount": 1500,                    // per window
  "quota_scope": "per_model"              // per_model/per_account
}
```

## Pruning Strategy

### What to prune
- Offers not seen in 30+ days (likely expired)
- Sources with 3+ consecutive failures (degraded)
- Old snapshots (keep last 7 days only)
- Event logs older than 30 days

### What NOT to prune
- Active deals with recent verification
- Historical events (append-only, never delete)
- Source configurations (always keep)

### Pruning schedule
- **Daily**: Remove snapshots older than 7 days
- **Weekly**: Archive event logs older than 30 days
- **Monthly**: Compact SQLite database

## How to keep it tidy

1. **One truth store** — SQLite only, no JSON snapshots
2. **Append-only events** — never delete, always append
3. **Content-addressed storage** — hash-based, no duplicates
4. **Canonical offer IDs** — stable identity across updates
5. **Evidence per claim** — every claim links to source
6. **Expiry tracking** — every deal has start/end dates (or "unknown")
