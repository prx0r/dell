#!/usr/bin/env python3
"""mcp/server.py — LLM Deals MCP server (MCP SDK v2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ListToolsRequest, CallToolRequest, ListToolsResult, CallToolResult

server = Server("llm-deals")

TOOLS = [
    Tool(name="find_inference_deals", description="Find current LLM inference deals.",
         inputSchema={"type": "object", "properties": {"task": {"type": "string"}, "max_price": {"type": "number"}, "free_only": {"type": "boolean"}, "limit": {"type": "integer", "default": 10}}}),
    Tool(name="compare_inference_offers", description="Compare all provider offerings for a model.",
         inputSchema={"type": "object", "properties": {"model": {"type": "string"}, "task": {"type": "string"}}}),
    Tool(name="get_deal_changes", description="Get recent deal changes.",
         inputSchema={"type": "object", "properties": {"since_hours": {"type": "integer", "default": 24}}}),
    Tool(name="explain_deal", description="Explain a deal: source, verification, alternatives.",
         inputSchema={"type": "object", "properties": {"model": {"type": "string"}, "provider": {"type": "string"}}}),
    Tool(name="get_providers", description="List all providers with setup info.",
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="get_provider_setup", description="Get setup instructions for a provider.",
         inputSchema={"type": "object", "properties": {"provider": {"type": "string"}}}),
    Tool(name="get_free_models", description="List all free models/offers.",
         inputSchema={"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}}),
    Tool(name="get_best_by_badge", description="Best models by category: workhorse, big-brain, coder, agentic, worker, free, fast.",
         inputSchema={"type": "object", "properties": {"badge": {"type": "string"}, "limit": {"type": "integer", "default": 10}}}),
    Tool(name="recommend_model", description="Recommend best model for a task with constraints.",
         inputSchema={"type": "object", "properties": {"task": {"type": "string"}, "max_cost": {"type": "number"}, "tool_calling": {"type": "boolean"}, "min_context": {"type": "integer"}}}),
    Tool(name="get_dataset_stats", description="Dataset statistics.",
         inputSchema={"type": "object", "properties": {}}),
]

def _load_offers():
    """Load offers from SQLite canonical DB, falling back to snapshots."""
    offers = []
    db_path = ROOT / "data" / "llmdeals.sqlite3"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM offers").fetchall()
            offers = [dict(r) for r in rows]
            conn.close()
            return offers
        except Exception:
            pass
    # Fallback to snapshots if DB not available
    d = ROOT / "snapshots"
    if d.exists():
        for f in d.glob("*.json"):
            try: offers.extend(json.loads(f.read_text()).get("offers", []))
            except: pass
    return offers

def _handle(name, args):
    offers = _load_offers()
    if name == "find_inference_deals":
        r = offers
        if args.get("free_only"): r = [o for o in r if o.get("free")]
        if args.get("max_price"): r = [o for o in r if (o.get("input_per_m") or 0) <= args["max_price"]]
        return {"deals": r[:args.get("limit", 10)], "count": len(r)}
    elif name == "compare_inference_offers":
        m = args.get("model", "")
        return {"model": m, "offerings": [o for o in offers if m.lower() in (o.get("model_id") or "").lower()]}
    elif name == "get_deal_changes":
        events = []
        ed = ROOT / "events"
        if ed.exists():
            for f in sorted(ed.glob("*.json"), reverse=True)[:10]:
                try:
                    ev = json.loads(f.read_text())
                    events.extend(ev if isinstance(ev, list) else [ev])
                except: pass
        return {"changes": events[:50]}
    elif name == "explain_deal":
        m = args.get("model", "")
        r = [o for o in offers if m.lower() in (o.get("model_id") or "").lower()]
        if args.get("provider"): r = [o for o in r if args["provider"].lower() in (o.get("provider_id") or "").lower()]
        return {"model": m, "results": r[:5]}
    elif name == "get_providers":
        import providers as pm
        return {"providers": [pm.to_dict(p) for p in pm.PROVIDERS.values()]}
    elif name == "get_provider_setup":
        import providers as pm
        p = pm.get_provider(args.get("provider", ""))
        if not p: return {"error": "Unknown provider"}
        return {"provider": p.name, "steps": p.setup_steps, "difficulty": p.setup_difficulty, "free_tier": p.free_tier}
    elif name == "get_free_models":
        return {"free_models": [o for o in offers if o.get("free")][:args.get("limit", 20)]}
    elif name == "get_best_by_badge":
        import scoring
        badge = args.get("badge", "workhorse")
        scored = [scoring.score_and_badge(o) for o in offers]
        badged = [s for s in scored if badge in (s.get("badges") or [])]
        badged.sort(key=lambda x: x["vector"]["workhorse"], reverse=True)
        return {"badge": badge, "picks": badged[:args.get("limit", 10)]}
    elif name == "recommend_model":
        import scoring
        return scoring.recommend(offers, task=args.get("task", "coding"), min_context=args.get("min_context", 0),
                                 tool_calling=args.get("tool_calling", False), budget=args.get("max_cost"), limit=5)
    elif name == "get_dataset_stats":
        return {"total": len(offers), "free": sum(1 for o in offers if o.get("free")),
                "providers": len(set(o.get("provider_id", "") for o in offers))}
    return {"error": f"Unknown tool: {name}"}

async def handle_list_tools(request=None):
    return ListToolsResult(tools=TOOLS)

async def handle_call_tool(request=None):
    name = request.params.name if request and hasattr(request, 'params') else ""
    args = request.params.arguments if request and hasattr(request, 'params') else {}
    result = _handle(name, args or {})
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, default=str))])

server.add_request_handler("tools/list", ListToolsRequest, handle_list_tools)
server.add_request_handler("tools/call", CallToolRequest, handle_call_tool)

async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
