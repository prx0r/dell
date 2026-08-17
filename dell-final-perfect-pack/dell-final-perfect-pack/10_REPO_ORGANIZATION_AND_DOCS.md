# Repo Organization and Documentation Convergence

## Current problem

Recent implementation has moved faster than canonical docs.

At inspected head, `AGENTS.md` still references an older SHA and older scoring/MCP file names.

This must not recur.

## Target root

```text
README.md
AGENTS.md
MANIFEST.json
pyproject.toml
Dockerfile
app/
mcp/
skills/
tests/
docs/
data/
```

## Active docs only

Keep:
- README.md
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/API.md
- docs/MCP.md
- docs/TRUST.md
- docs/SCORING.md
- docs/OPERATIONS.md
- docs/TESTING.md

Move historical review/thesis files to:
`docs/archive/`

## Machine source of truth

`MANIFEST.json` should be generated and include:

- git SHA
- schema version
- migration count
- API routes
- MCP tool names
- active scoring version
- active DecisionService version
- test commands
- latest certificate ID
- live dataset counts
- coverage summaries

Generate README/AGENTS dynamic sections from this manifest.

Do not hand-edit counts.

## Delete/deprecate duplicated paths

Once parity is proven:
- old scoring engine cannot remain imported by active code
- old categories cannot remain active
- old MCP servers cannot remain executable in normal docs
- recommendation functions outside DecisionService should be deleted or explicitly archived

## README executable test

In a clean container:

1. follow install commands exactly
2. run migrations
3. start API
4. make first `/resolve` call
5. start MCP
6. call one MCP tool
7. run tests

If README steps fail, release fails.
