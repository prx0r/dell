// web/src/lib/models.js — read the canonical models JSON + compute rankings (build-time)
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// the canonical DB is at /root/dealradar/data/canonical-models.json (absolute — robust to build dir)
const DB = '/root/dealradar/data/canonical-models.json';

const TASK_BENCHMARKS = {
  coding: ['SWE-Bench Verified', 'SWE-Bench Pro', 'Terminal-Bench', 'Aider Polyglot', 'Artificial Analysis Coding Index'],
  reasoning: ["Humanity's Last Exam", 'SciCode', 'GPQA'],
};

function norm(score) {
  const s = Number(score);
  if (isNaN(s)) return 0;
  return Math.max(0, Math.min(s, 100));
}

function benchmarkQuality(modelId, rec, task) {
  const bmarks = rec.benchmarks || [];
  if (!bmarks.length) return { score: null, source: 'estimated' };
  for (const wanted of (TASK_BENCHMARKS[task] || [])) {
    const kw = wanted.toLowerCase().split(' ')[0] + '-';
    for (const b of bmarks) {
      const name = (b.name || '').toLowerCase();
      if (kw && (name.includes(kw) || name.includes(wanted.toLowerCase()))) {
        const s = norm(b.score);
        if (s > 0) return { score: s, source: 'measured', benchmark: b.name };
      }
    }
  }
  const coding = bmarks.filter((b) => /SWE|Terminal|Aider|Coding/.test(b.name || ''));
  if (coding.length) {
    const b = coding.reduce((a, c) => (norm(c.score) > norm(a.score) ? c : a), coding[0]);
    return { score: norm(b.score), source: 'measured', benchmark: b.name };
  }
  return { score: null, source: 'estimated' };
}

function isJunk(mid, rec) {
  const low = mid.toLowerCase();
  const junk = ['embedding', 'audio', 'tts', 'stt', 'whisper', 'stable-diffusion', 'flux', 'dall-e',
                'sdxl', 'rerank', 'colbert', 'ollama/', 'sample_spec', 'bedrock/', 'ssd-1b', 'playground',
                '1024', 'canvas', 'img', 'video'];
  if (junk.some((x) => low.includes(x))) return true;
  if ((rec.provider || '').toLowerCase().includes('embedding')) return true;
  return false;
}

export function ranked(task = 'coding', limit = 10, prefer_free = false) {
  const db = JSON.parse(readFileSync(DB, 'utf8'));
  const out = [];
  for (const [mid, rec] of Object.entries(db.models || {})) {
    if (isJunk(mid, rec)) continue;
    const free = rec.free || (rec.prompt_per_token === 0 && rec.completion_per_token === 0);
    if (prefer_free && !free) continue;
    const bq = benchmarkQuality(mid, rec, task);
    // cost per task (20k in / 4k out)
    const cost = (rec.prompt_per_token || 0) * 20000 + (rec.completion_per_token || 0) * 4000;
    // score: measured benchmark if available, else a quality estimate; prefer cheap+free
    const quality = bq.score ?? 40;
    const score = free ? quality * 10 : (quality * 10) / (cost > 0 ? cost : 1);
    out.push({ model: mid, provider: rec.provider, free, benchmark: bq.benchmark,
               benchmark_score: bq.score, cost, score: Math.round(score) });
  }
  out.sort((a, b) => b.score - a.score);
  return out.slice(0, limit);
}

export function visionModels(limit = 8) {
  const db = JSON.parse(readFileSync(DB, 'utf8'));
  const out = [];
  for (const [mid, rec] of Object.entries(db.models || {})) {
    if (isJunk(mid, rec)) continue;
    if (!(rec.input_modalities || []).includes('image')) continue;
    const cost = (rec.prompt_per_token || 0) * 20000 + (rec.completion_per_token || 0) * 4000;
    out.push({ model: mid, provider: rec.provider, free: rec.free, cost,
               modalities: rec.input_modalities });
  }
  out.sort((a, b) => (a.cost || 0) - (b.cost || 0));
  return out.slice(0, limit);
}

export function freeModels(limit = 8) {
  return ranked('coding', limit, true);
}
