# Oracle Architecture — From Dell to Empirical Infrastructure Intelligence

## Core Insight

> **Oracle is not the LLM deals database. Oracle is the evidence-backed knowledge graph of machine-executable resources.**

## The Stack

```
COLLECTORS
Dell          → models/endpoints/pricing/quotas/promos
MCPWatch      → MCP servers/tools/APIs
AgentWatch    → agents/frameworks/skills
VidWatch      → video models/workflows/Comfy graphs
ComputeWatch  → GPUs/cloud/local/decentralized compute
BenchmarkWatch→ evals/performance observations

                    ↓

                ORACLE CORE
 identity
 observations
 artifacts
 claims/assertions
 evidence
 temporal validity
 reconciliation
 relationships
 measurements
 compatibility

                    ↓

              ORACLE RESOLVER
 "Given task + constraints, what resources/composition should I use?"

                    ↓

                 HOTLOADER
 "Instantiate/execute the chosen composition"
```

## Product Ladder

```
Level 1: CATALOG — what exists
Level 2: TRUTH — what's actually there (evidence-backed)
Level 3: MEASUREMENT — how it performs
Level 4: COMPATIBILITY — what works together
Level 5: ARCHITECTURE — compositions of resources
Level 6: OPTIMIZATION — best composition for task
Level 7: EXECUTION — instantiate and run
```

## Dell's Job (Levels 1-2)

```
What inference resources exist?
What are the actual serving endpoints?
What do they cost?
What quota/eligibility applies?
Is that still true?
What evidence proves it?
How has it changed?
What measured properties do we know?
```

## Oracle Core — Universal Evidence Kernel

### Resource Primitives

```
Resource
ResourceVersion
Endpoint
Capability
Interface
Assertion
Observation
Artifact
Measurement
Relationship
Constraint
Offer
Architecture
Evaluation
```

### Domain-Specific Payloads

**Dell produces:**
```
ASSERTION:
endpoint X
has_price
$0.14/M input

ASSERTION:
endpoint X
has_quota
30100 requests / rolling 5 hours

ASSERTION:
endpoint X
serves
MiMo-V2.5
```

**MCPWatch produces:**
```
ASSERTION:
server Y
provides_capability
github.issue.create
```

**VidWatch produces:**
```
ASSERTION:
workflow Z
requires
24GB VRAM
```

## Architecture Object (Killer Abstraction)

```json
{
  "architecture_id": "autonomous-repo-maintainer-v4",
  "task_classes": ["repo_maintenance", "bugfix", "code_review"],
  "requires": [
    {"capability": "agent.runtime"},
    {"capability": "model.code_generation"},
    {"capability": "tool.github"},
    {"capability": "tool.shell"}
  ],
  "optional": [
    {"capability": "memory.long_term"}
  ],
  "measurements": {
    "task_success": {
      "value": 0.84,
      "benchmark_id": "oracle-repo-maint-v2"
    }
  }
}
```

Oracle resolves:
```
Architecture
    ↓
OpenCode
    ↓
MiMo V2.5 @ OpenCode Go
    ↓
GitHub tool
    ↓
repo-map skill
    ↓
test runner
```

If MiMo deal disappears, Oracle resolves to another compatible model.

## Development Phases

### Phase 1: Dell Oracle-1
Make Dell's evidence model genuinely trustworthy:
- Exact observation linkage
- Immutable artifacts
- Field assertions
- Stale/conflicted/unknown semantics
- Claim-specific freshness
- Real negative observations
- Reconciliation

### Phase 2: Extract Oracle Core
Lift generic pieces into separate package/service.
Do not design Oracle abstractly first; let Dell's edge cases forge it.

### Phase 3: Second Vertical as Proof
Ingest MCP/tool infrastructure. If Oracle Core handles both inference economics and MCP resources without hacks, the abstraction is valid.

**Do not start with all five collectors. Dell + MCPWatch is enough to prove the thesis.**

## The Moat

Catalogs can be copied.
Rankings can be copied.
Architecture templates can be copied.

What becomes hard to copy:

```
3 years of observations
+
source reliability history
+
endpoint performance measurements
+
price histories
+
compatibility failures
+
architecture benchmark results
+
real execution outcomes
```

Then Oracle starts learning things nobody has explicitly published:

```
"This provider advertises 128K but failures rise sharply above 80K."

"This architecture gets 92% of the performance of the frontier stack at 11% of the cost."

"This MCP server's schema is compatible, but its real tool success rate is poor."

"This video workflow becomes unreliable below 20GB VRAM."

"This 'free' provider has 99.6% availability in Europe but 71% in Southeast Asia."
```

At that stage Oracle is no longer a registry.

It is **empirical infrastructure intelligence**.

## Oracle-1 Milestone (Seven Invariants)

```
1. Every served factual field traces to ≥1 exact claim
2. Every claim traces to exact immutable observed bytes
3. No stale fact silently masquerades as current
4. Absence, unknown, stale, conflicted and false are distinct
5. No projection overwrites historical observation truth
6. "Verified" is multidimensional and claim-specific
7. Every production invariant has a test capable of genuinely failing
```
