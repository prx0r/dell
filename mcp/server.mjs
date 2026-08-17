#!/usr/bin/env node
// mcp/server.mjs — LLM Deals MCP server (safe, no code injection)
// Register: hermes mcp add llm-deals --command node --args /root/ass-rape-spunk-porn/mcp/server.mjs
import { spawnSync } from "node:child_process";
import process from "node:process";

const ROOT = "/root/ass-rape-spunk-porn";
const PY = "python3";
const RUNNER = `${ROOT}/mcp/tool_runner.py`;

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
    // SAFE: pass args as JSON string to tool_runner.py, no code injection
    const p = spawnSync(PY, [RUNNER, name, JSON.stringify(args || {})],
      { cwd: ROOT, encoding: "utf8", env: { ...process.env, PYTHONPATH: `${ROOT}/app` } });
    let result;
    try { result = JSON.parse(p.stdout || '{"error":"tool execution failed"}'); }
    catch(e) { result = {"error": `Parse error: ${p.stdout}`}; }
    send({ jsonrpc: "2.0", id: msg.id, result: {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }]
    }});
  }
}

const TOOLS = [
  { name: "find_inference_deals", description: "Find current LLM inference deals by task, price, free status.",
    inputSchema: { type: "object", properties: { task: {type:"string"}, max_price: {type:"number"}, free_only: {type:"boolean"}, limit: {type:"integer",default:10} } } },
  { name: "get_free_models", description: "List all free models/offers.",
    inputSchema: { type: "object", properties: { limit: {type:"integer",default:20} } } },
  { name: "get_providers", description: "List all providers with setup info.",
    inputSchema: { type: "object", properties: {} } },
  { name: "get_provider_setup", description: "Get step-by-step setup instructions for a provider.",
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
