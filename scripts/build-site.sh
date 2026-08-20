#!/bin/bash
# scripts/build-site.sh — Export SQLite to snapshots, then build Astro site
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Dell Site Build ==="

# Step 1: Export SQLite to snapshots
echo "Step 1: Exporting SQLite to snapshots/..."
if [ -f "data/llmdeals.sqlite3" ]; then
    python3 scripts/export-snapshots.py
else
    echo "WARNING: No SQLite DB found. Site will build with empty data."
    echo "  Run: python3 -m app.cron_poll  (to populate the DB first)"
    mkdir -p snapshots
    echo '{"count":0,"offers":[]}' > snapshots/all-offers.json
fi

# Step 2: Build Astro site
echo "Step 2: Building Astro site..."
cd web
if [ ! -d "node_modules" ]; then
    echo "  Installing dependencies..."
    npm install
fi
npx astro build
echo ""
echo "=== Build complete ==="
echo "  Output: web/dist/"
echo "  Preview: npx astro preview"
