#!/bin/bash
# Hermes autonomous testing loop
# Runs Hermes against the MCP tools, logs everything

LOG="data/tests/hermes-test-$(date +%Y%m%d-%H%M%S).log"
mkdir -p data/tests

echo "=== HERMES AUTONOMOUS TEST $(date) ===" | tee "$LOG"

# Test 1: Basic stats
echo "" | tee -a "$LOG"
echo "TEST 1: Dataset stats" | tee -a "$LOG"
hermes -z "Call get_dataset_stats and tell me the total offers, free count, and provider count. Just the numbers." --yolo 2>&1 | tee -a "$LOG"

# Test 2: Find cheapest coding
echo "" | tee -a "$LOG"
echo "TEST 2: Cheapest coding model" | tee -a "$LOG"
hermes -z "Call find_inference_deals with task=coding and max_price=0.5 and limit=3. List the model names and prices." --yolo 2>&1 | tee -a "$LOG"

# Test 3: Free models
echo "" | tee -a "$LOG"
echo "TEST 3: Free models" | tee -a "$LOG"
hermes -z "Call get_free_models with limit=5. List the model names, providers, and context windows." --yolo 2>&1 | tee -a "$LOG"

# Test 4: Provider setup
echo "" | tee -a "$LOG"
echo "TEST 4: Provider setup" | tee -a "$LOG"
hermes -z "Call get_provider_setup with provider=deepseek. Give me the exact steps." --yolo 2>&1 | tee -a "$LOG"

# Test 5: Explain a deal
echo "" | tee -a "$LOG"
echo "TEST 5: Explain MiMo deal" | tee -a "$LOG"
hermes -z "Call explain_deal with model=opencode-go/mimo-v2.5. Tell me everything about this deal." --yolo 2>&1 | tee -a "$LOG"

# Test 6: Best workhorse
echo "" | tee -a "$LOG"
echo "TEST 6: Best workhorses" | tee -a "$LOG"
hermes -z "Call get_best_by_badge with badge=workhorse and limit=5. List the top 5 models with their scores." --yolo 2>&1 | tee -a "$LOG"

# Test 7: Recommend for agentic coding
echo "" | tee -a "$LOG"
echo "TEST 7: Recommend for agentic coding" | tee -a "$LOG"
hermes -z "Call recommend_model with task=coding and tool_calling=true and limit=3. What model should I use?" --yolo 2>&1 | tee -a "$LOG"

# Test 8: Try to confuse it
echo "" | tee -a "$LOG"
echo "TEST 8: Confusion attempts" | tee -a "$LOG"
hermes -z "Call find_inference_deals with task=nonexistent_task and max_price=-1 and limit=-5. What happens?" --yolo 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== TEST COMPLETE $(date) ===" | tee -a "$LOG"
echo "Log: $LOG"
