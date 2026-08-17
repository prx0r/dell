#!/usr/bin/env python3
"""mcp/tool_runner.py — Safe tool runner for MCP server.

Takes tool name + JSON args via stdin, runs the tool, outputs JSON result.
No code injection possible — arguments are parsed as JSON, not interpolated into source.
"""
import sys
import json
import os

ROOT = Path(__file__).resolve().parents[1] if "__file__" in dir() else Path("/root/ass-rape-spunk-porn")
sys.path.insert(0, str(ROOT / "app"))

from pathlib import Path

def load_offers():
    offers = []
    snapshots_dir = ROOT / "snapshots"
    if snapshots_dir.exists():
        for f in snapshots_dir.glob("*.json"):
            try:
                offers.extend(json.loads(f.read_text()).get("offers", []))
            except Exception:
                pass
    return offers

def run_tool(name, args):
    args = args or {}
    offers = load_offers()

    if name == "find_inference_deals":
        r = offers
        if args.get("free_only"):
            r = [o for o in r if o.get("free")]
        max_price = args.get("max_price")
        if max_price is not None:
            r = [o for o in r if o.get("input_per_m") is not None and o["input_per_m"] <= max_price]
        limit = args.get("limit", 10)
        return {"deals": r[:limit], "count": len(r)}

    elif name == "get_free_models":
        limit = args.get("limit", 20)
        free = [o for o in offers if o.get("free")]
        return {"free_models": free[:limit], "count": len(free)}

    elif name == "get_providers":
        import providers as pm
        return {"providers": [pm.to_dict(p) for p in pm.PROVIDERS.values()]}

    elif name == "get_provider_setup":
        import providers as pm
        p = pm.get_provider(args.get("provider", ""))
        if not p:
            return {"error": "Unknown provider"}
        return {"provider": p.name, "steps": p.setup_steps, "difficulty": p.setup_difficulty, "free_tier": p.free_tier}

    elif name == "get_best_by_badge":
        import scoring
        badge = args.get("badge", "workhorse")
        limit = args.get("limit", 10)
        scored = [scoring.score_and_badge(o) for o in offers]
        badged = [s for s in scored if badge in (s.get("badges") or [])]
        badged.sort(key=lambda x: x["vector"]["workhorse"], reverse=True)
        return {"badge": badge, "picks": [{k: v for k, v in b.items() if k in ("model_id", "provider_id", "vector", "badges")} for b in badged[:limit]], "count": len(badged)}

    elif name == "recommend_model":
        import scoring
        return scoring.recommend(offers, task=args.get("task", "coding"),
                                 min_context=args.get("min_context", 0),
                                 tool_calling=args.get("tool_calling", False),
                                 budget=args.get("max_cost"), limit=5)

    elif name == "get_deal_changes":
        events = []
        ed = ROOT / "events"
        if ed.exists():
            for f in sorted(ed.glob("*.json"), reverse=True)[:10]:
                try:
                    ev = json.loads(f.read_text())
                    events.extend(ev if isinstance(ev, list) else [ev])
                except Exception:
                    pass
        return {"changes": events[:50], "count": len(events)}

    elif name == "explain_deal":
        model = args.get("model", "")
        provider = args.get("provider")
        r = [o for o in offers if model.lower() in (o.get("model_id") or "").lower()]
        if provider:
            r = [o for o in r if provider.lower() in (o.get("provider_id") or "").lower()]
        return {"model": model, "results": r[:5]}

    elif name == "get_dataset_stats":
        free = sum(1 for o in offers if o.get("free"))
        providers = set(o.get("provider_id", "") for o in offers)
        return {"total": len(offers), "free": free, "providers": len(providers)}

    return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    # Read tool name and args from command line (safe — no code injection)
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: tool_runner.py <tool_name> [json_args]"}))
        sys.exit(1)

    tool_name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    result = run_tool(tool_name, args)
    print(json.dumps(result, default=str))
