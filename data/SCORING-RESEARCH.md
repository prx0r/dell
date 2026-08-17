# Scoring Research Validation

## Current Scoring System

### Dimensions (7)
1. Intelligence — benchmark scores
2. Coding — coding benchmarks
3. Reasoning — reasoning benchmarks
4. Agentic — agentic benchmarks
5. Speed — throughput tps
6. Cost — real pricing
7. Context — context window
8. Reliability — provider health
9. Tool calling — model capability

### Badges (10)
- mega_deal: ≥3x capacity or ≥2x usage
- frontier: intelligence ≥ 80
- workhorse: composite ≥ 70
- coder: coding ≥ 70
- agentic: agentic ≥ 60 AND tool_calling ≥ 60
- fast: speed ≥ 80
- hidden_gem: value ≥ 80
- free: is_free
- long_context: context ≥ 80
- tool_caller: tool_calling ≥ 75

---

## Research to Validate Against

### 1. LLMRouterBench (ACL 2026)
- Benchmarks predict real-world task performance
- Our approach: median of available benchmarks
- Status: ✅ Aligned

### 2. Databricks Real-World Task Completion
- Value = intelligence × cost_efficiency
- Our approach: value = intelligence × cost_score / 100
- Status: ✅ Aligned

### 3. Artificial Analysis Intelligence Scores
- They measure actual inference quality
- We use their data as one source
- Status: ✅ Using their data

### 4. OpenRouter Provider Selection
- They use performance/uptime for routing
- We could use similar metrics
- Status: ⚠️ Not yet implemented

### 5. GPQA / MMLU-Pro Benchmarks
- Standard reasoning benchmarks
- We include them in reasoning score
- Status: ✅ Aligned

### 6. SWE-Bench Verified
- Standard coding benchmark
- We include it in coding score
- Status: ✅ Aligned

---

## What's Missing (Research-Backed)

### 1. Real Performance Metrics
- We use throughput_tps from HF Router
- But we don't have our own measurements
- Status: ⚠️ Partial

### 2. Provider Reliability
- We use a fixed 70 baseline
- Should use actual fetch success rate
- Status: ⚠️ Placeholder

### 3. Tool Calling Quality
- We use a boolean (tool_call=True/False)
- Should measure actual tool success rate
- Status: ⚠️ Oversimplified

### 4. Multi-Turn Performance
- We don't measure conversation quality
- Important for agentic tasks
- Status: ❌ Not implemented

### 5. Context Window Effectiveness
- We use advertised context
- Should measure effective context
- Status: ⚠️ Not measured

---

## Recommended Changes

### Immediate
1. Fix reliability to use actual fetch success rate
2. Add tool calling quality measurement
3. Validate against GPQA/SWE-Bench scores

### Medium-term
4. Add multi-turn performance metrics
5. Add effective context measurement
6. Add provider uptime tracking

### Long-term
7. Add real-world task completion rates
8. Add cost-per-task calculations
9. Add routing optimization based on historical performance
