#!/bin/bash
# dell-cron-wake.sh — Hermes wakes up to this on schedule
# Sets up the environment, runs the orchestration skill, logs everything

set -euo pipefail

DELL_ROOT="/mnt/HC_Volume_106427611/dell"
LOG_DIR="$DELL_ROOT/data/cron-logs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/wake-$TIMESTAMP.log"
SUMMARY_FILE="$LOG_DIR/wake-$TIMESTAMP.json"

mkdir -p "$LOG_DIR"

echo "=== DELL CRON WAKE $TIMESTAMP ===" | tee "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Step 1: Quick health check (30s max)
echo "--- STEP 1: HEALTH CHECK ---" | tee -a "$LOG_FILE"
cd "$DELL_ROOT"

# Check API is up
API_OK=false
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8803/v1/models 2>/dev/null | grep -q "200"; then
    API_OK=true
    echo "API: UP" | tee -a "$LOG_FILE"
else
    echo "API: DOWN (will use SQLite directly)" | tee -a "$LOG_FILE"
fi

# Check SQLite exists
DB="$DELL_ROOT/data/llmdeals.sqlite3"
if [ -f "$DB" ]; then
    DB_SIZE=$(du -h "$DB" | cut -f1)
    echo "DB: EXISTS ($DB_SIZE)" | tee -a "$LOG_FILE"
else
    echo "DB: MISSING — will run discovery first" | tee -a "$LOG_FILE"
fi

# Step 2: Assess state
echo "" | tee -a "$LOG_FILE"
echo "--- STEP 2: STATE ASSESSMENT ---" | tee -a "$LOG_FILE"

if [ -f "$DB" ]; then
    python3 -c "
import sqlite3, json
from datetime import datetime, timezone

conn = sqlite3.connect('$DB')
conn.row_factory = sqlite3.Row

total = conn.execute('SELECT COUNT(*) as cnt FROM offers').fetchone()['cnt']
free = conn.execute('SELECT COUNT(*) as cnt FROM offers WHERE free = 1').fetchone()['cnt']
providers = conn.execute('SELECT COUNT(DISTINCT provider_id) as cnt FROM offers').fetchone()['cnt']
stale = conn.execute('''
    SELECT COUNT(*) as cnt FROM offers
    WHERE updated_at < datetime('now', '-1 day')
''').fetchone()['cnt']

# Check last discovery run
last_run = conn.execute('''
    SELECT MAX(created_at) as lr FROM offers
''').fetchone()['lr'] or 'never'

state = {
    'total_offers': total,
    'free_offers': free,
    'providers': providers,
    'stale_count': stale,
    'last_discovery': last_run,
    'db_exists': True
}
print(json.dumps(state, indent=2))
conn.close()
" | tee -a "$LOG_FILE"
else
    echo '{"db_exists": false, "action": "run_discovery_first"}' | tee -a "$LOG_FILE"
fi

# Step 3: Run orchestration based on state
echo "" | tee -a "$LOG_FILE"
echo "--- STEP 3: ORCHESTRATION ---" | tee -a "$LOG_FILE"

# Decide which track to run
TRACK="health"
if [ -f "$DB" ]; then
    STALE_COUNT=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB')
c = conn.execute(\"SELECT COUNT(*) FROM offers WHERE updated_at < datetime('now', '-1 day')\").fetchone()[0]
print(c)
conn.close()
" 2>/dev/null || echo "0")

    if [ "$STALE_COUNT" -gt 100 ]; then
        TRACK="freshness"
    fi
fi

echo "Track selected: $TRACK" | tee -a "$LOG_FILE"

case "$TRACK" in
    freshness)
        echo "Running Track A: Data Freshness" | tee -a "$LOG_FILE"
        # Run discovery
        cd "$DELL_ROOT"
        PYTHONPATH=app:. python3 -c "
from app.discovery import run_discovery
result = run_discovery(sources=['opencode-go', 'rss-feeds', 'hackernews'])
import json
print(json.dumps(result, indent=2, default=str)[:3000])
" 2>&1 | tee -a "$LOG_FILE" || echo "Discovery failed" | tee -a "$LOG_FILE"
        ;;

    health|*)
        echo "Running Track C: Health Check" | tee -a "$LOG_FILE"
        # Run watchdog
        cd "$DELL_ROOT"
        python3 agent/watchdog.py 2>&1 | tee -a "$LOG_FILE" || echo "Watchdog failed" | tee -a "$LOG_FILE"
        ;;
esac

# Step 4: Summary
echo "" | tee -a "$LOG_FILE"
echo "--- STEP 4: SUMMARY ---" | tee -a "$LOG_FILE"

# Count what we have now
if [ -f "$DB" ]; then
    python3 -c "
import sqlite3, json
conn = sqlite3.connect('$DB')
conn.row_factory = sqlite3.Row
total = conn.execute('SELECT COUNT(*) as cnt FROM offers').fetchone()['cnt']
free = conn.execute('SELECT COUNT(*) as cnt FROM offers WHERE free = 1').fetchone()['cnt']
providers = conn.execute('SELECT COUNT(DISTINCT provider_id) as cnt FROM offers').fetchone()['cnt']
print(json.dumps({'final_total': total, 'final_free': free, 'final_providers': providers}))
conn.close()
" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "=== DELL CRON WAKE COMPLETE $(date) ===" | tee -a "$LOG_FILE"

# Write summary JSON
cat > "$SUMMARY_FILE" <<EOF
{
    "timestamp": "$TIMESTAMP",
    "track": "$TRACK",
    "api_up": $API_OK,
    "log_file": "$LOG_FILE",
    "status": "completed"
}
EOF

echo "Summary: $SUMMARY_FILE"
