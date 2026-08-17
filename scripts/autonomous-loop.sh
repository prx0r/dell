#!/bin/bash
# Autonomous testing loop
# Hermes tests → we analyze → fix → repeat until clean

MAX_ROUNDS=5
LOG_DIR="data/tests/autonomous"
mkdir -p "$LOG_DIR"

echo "=== AUTONOMOUS LOOP STARTING $(date) ===" | tee "$LOG_DIR/loop.log"

for ROUND in $(seq 1 $MAX_ROUNDS); do
    echo "" | tee -a "$LOG_DIR/loop.log"
    echo "=== ROUND $ROUND $(date) ===" | tee -a "$LOG_DIR/loop.log"

    # Run Hermes user test
    hermes -z "You are testing an LLM deals API. You need cheap inference for a coding agent. Use the MCP tools to find deals. Be critical — note anything broken, unclear, or missing. Report issues as a numbered list." --yolo 2>&1 > "$LOG_DIR/round-${ROUND}-hermes.txt"

    # Check for issues in the output
    ISSUES=$(grep -c "issue\|broken\|unclear\|missing\|wrong\|error\|bug\|problem" "$LOG_DIR/round-${ROUND}-hermes.txt" 2>/dev/null || echo "0")
    echo "Issues found: $ISSUES" | tee -a "$LOG_DIR/loop.log"

    # If no issues, we're done
    if [ "$ISSUES" -eq 0 ]; then
        echo "ROUND $ROUND: No issues found — CLEAN!" | tee -a "$LOG_DIR/loop.log"
        break
    fi

    # Show the issues
    echo "Issues in round $ROUND:" | tee -a "$LOG_DIR/loop.log"
    grep -i "issue\|broken\|unclear\|missing\|wrong\|bug\|problem" "$LOG_DIR/round-${ROUND}-hermes.txt" | head -10 | tee -a "$LOG_DIR/loop.log"

    # Save for analysis
    cp "$LOG_DIR/round-${ROUND}-hermes.txt" "$LOG_DIR/round-${ROUND}-analysis.txt"

    echo "" | tee -a "$LOG_DIR/loop.log"
    echo "ROUND $ROUND COMPLETE — $ISSUES issues to fix" | tee -a "$LOG_DIR/loop.log"

    # Brief pause between rounds
    sleep 2
done

echo "" | tee -a "$LOG_DIR/loop.log"
echo "=== AUTONOMOUS LOOP COMPLETE $(date) ===" | tee -a "$LOG_DIR/loop.log"
