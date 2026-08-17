# Architecture

## System Overview

```
DecisionService ← REST + MCP
      ↓
Canonical SQLite
      ↓
Evidence → Claims → Assertions → Offers → Routes
```

## Key Components

- DecisionService: Canonical resolver
- QueryService: Shared REST/MCP logic
- ScoringV3: Task-dependent scoring
- BadgeEngine: Semantic badges

## Data Flow

1. Sources → Observations → Artifacts
2. Artifacts → Claims → Assertions
3. Assertions → Offers → Routes
4. Routes → DecisionService → Recommendations
