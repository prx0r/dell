#!/usr/bin/env python3
"""app/gap_report.py — Nightly FREE INTELLIGENCE GAP REPORT

Identifies what's unknown about free routes and prioritizes investigation.
"""
import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import canonical_db


def generate_gap_report():
    """Generate gap report for all free endpoints."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    # Get all free endpoints
    endpoints = conn.execute("""
        SELECT endpoint_id, model_id, serving_provider_id, quantization,
               context_tokens, max_output_tokens, supports_tools,
               latency_p50_ms, throughput_p50_tps, availability_state
        FROM serving_endpoints WHERE is_free = 1
    """).fetchall()
    
    gaps = {
        "fully_characterized": [],
        "missing_quantization": [],
        "missing_performance": [],
        "missing_context": [],
        "missing_capabilities": [],
        "missing_quota": [],
    }
    
    for ep in endpoints:
        issues = []
        
        if ep['quantization'] == 'UNKNOWN':
            issues.append("quantization")
        
        if ep['latency_p50_ms'] is None:
            issues.append("latency")
        
        if ep['throughput_p50_tps'] is None:
            issues.append("throughput")
        
        if ep['context_tokens'] is None:
            issues.append("context")
        
        if ep['supports_tools'] is None:
            issues.append("tool_support")
        
        if not issues:
            gaps["fully_characterized"].append(ep['endpoint_id'])
        else:
            if "quantization" in issues:
                gaps["missing_quantization"].append(ep['endpoint_id'])
            if "latency" in issues or "throughput" in issues:
                gaps["missing_performance"].append(ep['endpoint_id'])
            if "context" in issues:
                gaps["missing_context"].append(ep['endpoint_id'])
            if "tool_support" in issues:
                gaps["missing_capabilities"].append(ep['endpoint_id'])
    
    # Check quota coverage
    providers_with_quota = set(r[0] for r in conn.execute(
        "SELECT DISTINCT provider FROM quota_policies"
    ).fetchall())
    
    providers_without = set(ep['serving_provider_id'] for ep in endpoints) - providers_with_quota
    gaps["missing_quota"] = list(providers_without)
    
    conn.close()
    
    # Calculate totals
    total = len(endpoints)
    characterized = len(gaps["fully_characterized"])
    
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_free_endpoints": total,
        "fully_characterized": characterized,
        "characterization_rate": round(characterized / total * 100, 1) if total > 0 else 0,
        "gaps": {k: len(v) for k, v in gaps.items()},
        "details": gaps,
    }
    
    return report


if __name__ == "__main__":
    report = generate_gap_report()
    
    print("=" * 70)
    print("FREE INTELLIGENCE GAP REPORT")
    print("=" * 70)
    print("\nTimestamp: %s" % report["timestamp"])
    print("Total free endpoints: %d" % report["total_free_endpoints"])
    print("Fully characterized: %d (%.1f%%)" % (
        report["fully_characterized"], report["characterization_rate"]))
    
    print("\nGAPS:")
    for gap, count in report["gaps"].items():
        print("  %s: %d" % (gap, count))
    
    print("\nPRIORITY INVESTIGATIONS:")
    for gap_name, items in report["details"].items():
        if items and gap_name != "fully_characterized":
            print("\n  %s (%d):" % (gap_name, len(items)))
            for item in items[:3]:
                print("    - %s" % item)
    
    # Save report
    report_path = ROOT / "data" / "tests" / ("gap-report-%s.json" % time.strftime("%Y%m%d-%H%M%S"))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print("\nReport saved to: %s" % report_path)
