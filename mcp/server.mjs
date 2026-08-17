#!/usr/bin/env node
// mcp/server.mjs — LLM Deals MCP server
// Reads from DealService (canonical DB), NOT snapshots
// Register: hermes mcp add llm-deals --command node --args /root/ass-rape-spunk-porn/mcp/server.mjs
import { spawnSync } from "node:child_process";
import process from "node:process";

const ROOT = "/root/ass-rape-spunk-porn";
const PY = "python3";

function runPy(script, args=[]) {
  const r = spawnSync(PY, [`${ROOT}/app/${script}`, ...args],
    { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
  return r.stdout || '{"error":"failed"}';
}

function pyOneLiner(code) {
  const r = spawnSync(PY, ["-c", code],
    { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
  try { return JSON.parse(r.stdout || "{}"); }
  catch(e) { return { error: r.stderr || "parse error" }; }
}

// MCP stdio server
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
      protocolVersion: "2024-11-05", capabilities: { tools: {} },
      serverInfo: { name: "llm-deals", version: "2.0" }
    }});
  } else if (msg.method === "notifications/initialized") {}
  else if (msg.method === "tools/list") {
    send({ jsonrpc: "2.0", id: msg.id, result: { tools: TOOLS }});
  } else if (msg.method === "tools/call") {
    const { name, arguments: args } = msg.params;
    let result;
    try { result = callTool(name, args || {}); }
    catch(e) { result = { error: e.message }; }
    send({ jsonrpc: "2.0", id: msg.id, result: {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }]
    }});
  }
}

function callTool(name, args) {
  const quote = (s) => JSON.stringify(String(s)).slice(1, -1);

  if (name === "get_dataset_stats") {
    return pyOneLiner(`
import sys; sys.path.insert(0,"${ROOT}/app")
from service import get_service
s = get_service()
print(json.dumps(s.get_stats()))
import json
`);
  }

  if (name === "list_models") {
    const limit = args.limit || 10;
    return pyOneLiner(`
import sys,json; sys.path.insert(0,"${ROOT}/app")
from service import get_service
s = get_service()
models = s.list_models(limit=${limit})
print(json.dumps({"models": models[:${limit}], "count": len(models)}))
`);
  }

  if (name === "list_providers") {
    return pyOneLiner(`
import sys,json; sys.path.insert(0,"${ROOT}/app")
import providers
print(json.dumps({"providers": [providers.to_dict(p) for p in providers.PROVIDERS.values()]}))
`);
  }

  if (name === "get_provider_setup") {
    const p = quote(args.provider || "");
    return pyOneLiner(`
import sys,json; sys.path.insert(0,"${ROOT}/app")
import providers
p = providers.get_provider("${p}")
if not p: print(json.dumps({"error":"Unknown provider"}))
else: print(json.dumps({"provider":p.name,"steps":p.setup_steps,"difficulty":p.setup_difficulty,"free_tier":p.free_tier}))
`);
  }

  if (name === "find_inference_deals") {
    const task = quote(args.task || "");
    const maxPrice = args.max_price || "null";
    const freeOnly = args.free_only ? "True" : "False";
    const limit = args.limit || 10;
    return pyOneLiner(`
import sys,json; sys.path.insert(0,"${ROOT}/app")
from service import get_service
s = get_service()
deals = s.list_deals(free=${freeOnly}, max_price=${maxPrice}, limit=${limit})
print(json.dumps({"deals": deals[:${limit}], "count": len(deals)}))
`);
  }

  if (name === "recommend_model") {
    const task = quote(args.task || "coding");
    const toolCalling = args.tool_calling ? "True" : "False";
    return pyOneLiner(`
import sys,json; sys.path.insert(0,"${ROOT}/app")
from service import get_service
import scoring
s = get_service()
offers_data = s.list_deals(limit=500)
result = scoring.recommend(offers_data, task="${task}", tool_calling=${toolCalling}, limit=5)
print(json.dumps(result, default=str))
`);
  }

  if (name === "explain_deal") {
    const model = quote(args.model || "");
    return pyOneLiner(`
import sys,json; sys.path.insert(0,"${ROOT}/app")
from service import get_service
s = get_service()
result = s.get_model("${model}")
print(json.dumps(result, default=str))
`);
  }

  if (name === "get_deal_changes") {
    const hours = args.since_hours || 24;
    return pyOneLiner(`
import sys,json; sys.path.insert(0,"${ROOT}/app")
from service import get_service
s = get_service()
changes = s.get_changes(since_hours=${hours})
print(json.dumps({"changes": changes[:50], "count": len(changes)}))
`);
  }

  if (name === "get_dataset_stats") {
    return pyOneLiner(`
import sys,json; sys.path.insert(0,"${ROOT}/app")
from service import get_service
s = get_service()
print(json.dumps(s.get_stats()))
`);
  }

  return { error: "Unknown tool: " + name };
}

const TOOLS = [
  { name: "get_dataset_stats", description: "Dataset statistics: total offers, free count, providers.",
    inputSchema: { type: "object", properties: {} } },
  { name: "list_models", description: "List models with providers and pricing.",
    inputSchema: { type: "object", properties: { search: {type:"string"}, limit: {type:"integer",default:10} } } },
  { name: "list_providers", description: "List all providers with setup info.",
    inputSchema: { type: "object", properties: {} } },
  { name: "get_provider_setup", description: "Step-by-step setup instructions for a provider.",
    inputSchema: { type: "object", properties: { provider: {type:"string"} } } },
  { name: "find_inference_deals", description: "Search deals by task, price, free status.",
    inputSchema: { type: "object", properties: { task: {type:"string"}, max_price: {type:"number"}, free_only: {type:"boolean"}, limit: {type:"integer",default:10} } } },
  { name: "recommend_model", description: "Recommend best model for a task.",
    inputSchema: { type: "object", properties: { task: {type:"string"}, tool_calling: {type:"boolean"}, limit: {type:"integer",default:5} } } },
  { name: "explain_deal", description: "Explain a deal: source, verification, alternatives.",
    inputSchema: { type: "object", properties: { model: {type:"string"}, provider: {type:"string"} } } },
  { name: "get_deal_changes", description: "Recent deal changes.",
    inputSchema: { type: "object", properties: { since_hours: {type:"integer",default:24} } } },
  { name: "get_dataset_stats", description: "Dataset statistics.",
    inputSchema: { type: "object", properties: {} } },
];
