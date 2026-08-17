#!/usr/bin/env node
// mcp/server.mjs — LLM Deals MCP server (Node.js stdio bridge, same pattern as patalafinal)
// Register: hermes mcp add llm-deals --command node --args /root/ass-rape-spunk-porn/mcp/server.mjs
import { spawnSync } from "node:child_process";
import process from "node:process";

const ROOT = "/root/ass-rape-spunk-porn";
const PY = "python3";

// Minimal stdio MCP server (JSON-RPC 2.0)
let buf = [];
process.stdin.on("data", (chunk) => {
  buf.push(chunk);
  const raw = buf.join("");
  const lines = raw.split("\n");
  buf = [];
  for (const line of lines) {
    if (!line.trim()) continue;
    try { handle(JSON.parse(line)); } catch(e) { buf.push(Buffer.from(line + "\n")); }
  }
});

function send(msg) { process.stdout.write(JSON.stringify(msg) + "\n"); }

function handle(msg) {
  if (msg.method === "initialize") {
    send({ jsonrpc: "2.0", id: msg.id, result: {
      protocolVersion: "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "llm-deals", version: "1.0" }
    }});
  } else if (msg.method === "notifications/initialized") {
    // noop
  } else if (msg.method === "tools/list") {
    send({ jsonrpc: "2.0", id: msg.id, result: { tools: TOOLS }});
  } else if (msg.method === "tools/call") {
    const { name, arguments: args } = msg.params;
    const result = runTool(name, args || {});
    send({ jsonrpc: "2.0", id: msg.id, result: {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }]
    }});
  }
}

function runTool(name, args) {
  const py = (script, extra_args=[]) => {
    const r = spawnSync(PY, [`${ROOT}/app/${script}`, ...extra_args],
      { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return { exit: r.status, stdout: (r.stdout||"").trim(), stderr: (r.stderr||"").trim() };
  };

  if (name === "find_inference_deals") {
    const r = py("api_canonical.py", []);
    // Parse the API response by running a quick Python one-liner
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json, os
offers=[]
for f in os.listdir("${ROOT}/snapshots"):
    if f.endswith(".json"):
        offers.extend(json.load(open(f"${ROOT}/snapshots/{f}")).get("offers",[]))
free_only = ${args.free_only ? "True" : "False"}
max_price = ${args.max_price || "None"}
limit = ${args.limit || 10}
r = offers
if free_only: r = [o for o in r if o.get("free")]
if max_price: r = [o for o in r if (o.get("input_per_m") or 0) <= max_price]
print(json.dumps({"deals": r[:limit], "count": len(r)}))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  if (name === "get_free_models") {
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json, os
offers=[]
for f in os.listdir("${ROOT}/snapshots"):
    if f.endswith(".json"):
        offers.extend(json.load(open(f"${ROOT}/snapshots/{f}")).get("offers",[]))
free = [o for o in offers if o.get("free")]
print(json.dumps({"free_models": free[:${args.limit||20}], "count": len(free)}))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  if (name === "get_providers") {
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json
from providers import PROVIDERS, to_dict
print(json.dumps({"providers": [to_dict(p) for p in PROVIDERS.values()]}))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  if (name === "get_provider_setup") {
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json
from providers import get_provider
p = get_provider("${args.provider||""}")
if not p: print(json.dumps({"error":"Unknown provider"}))
else: print(json.dumps({"provider":p.name,"steps":p.setup_steps,"difficulty":p.setup_difficulty,"free_tier":p.free_tier}))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  if (name === "get_best_by_badge") {
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json, os, scoring
offers=[]
for f in os.listdir("${ROOT}/snapshots"):
    if f.endswith(".json"):
        offers.extend(json.load(open(f"${ROOT}/snapshots/{f}")).get("offers",[]))
badge = "${args.badge||"workhorse"}"
scored = [scoring.score_and_badge(o) for o in offers]
badged = [s for s in scored if badge in (s.get("badges") or [])]
badged.sort(key=lambda x: x["vector"]["workhorse"], reverse=True)
print(json.dumps({"badge":badge,"picks":[{k:v for k,v in b.items() if k in ("model_id","provider_id","vector","badges")} for b in badged[:${args.limit||10}]],"count":len(badged)}))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  if (name === "recommend_model") {
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json, os, scoring
offers=[]
for f in os.listdir("${ROOT}/snapshots"):
    if f.endswith(".json"):
        offers.extend(json.load(open(f"${ROOT}/snapshots/{f}")).get("offers",[]))
r = scoring.recommend(offers, task="${args.task||"coding"}", min_context=${args.min_context||0},
    tool_calling=${args.tool_calling?"True":"False"}, budget=${args.max_cost||"None"}, limit=5)
print(json.dumps(r, default=str))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  if (name === "get_dataset_stats") {
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json, os
offers=[]
for f in os.listdir("${ROOT}/snapshots"):
    if f.endswith(".json"):
        offers.extend(json.load(open(f"${ROOT}/snapshots/{f}")).get("offers",[]))
free=sum(1 for o in offers if o.get("free"))
providers=set(o.get("provider_id","") for o in offers)
print(json.dumps({"total":len(offers),"free":free,"providers":len(providers)}))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  if (name === "get_deal_changes") {
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json, os
events=[]
ed = "${ROOT}/events"
if os.path.exists(ed):
    for f in sorted(os.listdir(ed)):
        if f.endswith(".json"):
            try:
                ev=json.load(open(f"{ed}/{f}"))
                events.extend(ev if isinstance(ev,list) else [ev])
            except: pass
print(json.dumps({"changes":events[-50:],"count":len(events)}))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  if (name === "explain_deal") {
    const p = spawnSync(PY, ["-c", `
import sys; sys.path.insert(0,"${ROOT}/app")
import json, os
offers=[]
for f in os.listdir("${ROOT}/snapshots"):
    if f.endswith(".json"):
        offers.extend(json.load(open(f"${ROOT}/snapshots/{f}")).get("offers",[]))
m = "${args.model||""}"
r = [o for o in offers if m.lower() in (o.get("model_id") or "").lower()]
p = "${args.provider||""}"
if p: r = [o for o in r if p.lower() in (o.get("provider_id") or "").lower()]
print(json.dumps({"model":m,"results":r[:5]}))
`], { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    return JSON.parse(p.stdout || '{"error":"failed"}');
  }

  return { error: `Unknown tool: ${name}` };
}

const TOOLS = [
  { name: "find_inference_deals", description: "Find current LLM inference deals by task, price, free status.",
    inputSchema: { type: "object", properties: { task: {type:"string"}, max_price: {type:"number"}, free_only: {type:"boolean"}, limit: {type:"integer",default:10} } } },
  { name: "get_free_models", description: "List all free models/offers.",
    inputSchema: { type: "object", properties: { limit: {type:"integer",default:20} } } },
  { name: "get_providers", description: "List all providers with setup info.",
    inputSchema: { type: "object", properties: {} } },
  { name: "get_provider_setup", description: "Get setup instructions for a provider.",
    inputSchema: { type: "object", properties: { provider: {type:"string"} } } },
  { name: "get_best_by_badge", description: "Best models by category: workhorse, big-brain, coder, agentic, worker, free, fast.",
    inputSchema: { type: "object", properties: { badge: {type:"string"}, limit: {type:"integer",default:10} } } },
  { name: "recommend_model", description: "Recommend best model for a task with constraints.",
    inputSchema: { type: "object", properties: { task: {type:"string"}, max_cost: {type:"number"}, tool_calling: {type:"boolean"}, min_context: {type:"integer"} } } },
  { name: "get_deal_changes", description: "Get recent deal changes.",
    inputSchema: { type: "object", properties: { since_hours: {type:"integer",default:24} } } },
  { name: "explain_deal", description: "Explain a deal: source, verification, alternatives.",
    inputSchema: { type: "object", properties: { model: {type:"string"}, provider: {type:"string"} } } },
  { name: "get_dataset_stats", description: "Dataset statistics.",
    inputSchema: { type: "object", properties: {} } },
];
