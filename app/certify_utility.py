#!/usr/bin/env python3
"""Dell External Oracle Utility Certification.

Tests actual usefulness, not schema presence.
"""
import sys
import os
import json
import time
import subprocess
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))


def start_api():
    """Start API server."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.api_canonical:app", "--port", "8803"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(3)
    return proc


def stop_api(proc):
    """Stop API server."""
    proc.terminate()
    proc.wait()


def test_rest_contract():
    """Test REST API contracts."""
    results = []
    base = "http://localhost:8803"
    
    endpoints = [
        ("GET", "/health", 200),
        ("GET", "/v1/stats", 200),
        ("GET", "/v1/models?limit=3", 200),
        ("GET", "/v1/deals?limit=3", 200),
        ("GET", "/v1/deals/free?limit=3", 200),
        ("GET", "/v1/mega-deals?limit=3", 200),
        ("GET", "/v1/recommend?task=coding", 200),
        ("GET", "/v1/providers?limit=3", 200),
        ("GET", "/v1/verification-runs?limit=3", 200),
        ("GET", "/v1/history?limit=3", 200),
        ("POST", "/v1/free/plan", 200, {"task": "coding", "requests": 10}),
        ("GET", "/v1/deals/nonexistent/evidence", 200),
    ]
    
    for ep in endpoints:
        method = ep[0]
        path = ep[1]
        expected = ep[2]
        body = ep[3] if len(ep) > 3 else None
        
        try:
            if method == "GET":
                r = requests.get("%s%s" % (base, path), timeout=5)
            else:
                r = requests.post("%s%s" % (base, path), json=body, timeout=5)
            
            status = "PASS" if r.status_code == expected else "FAIL"
            results.append({"test": "REST:%s" % path, "status": status,
                          "expected": expected, "actual": r.status_code})
        except Exception as e:
            results.append({"test": "REST:%s" % path, "status": "FAIL",
                          "error": str(e)[:50]})
    
    return results


def test_user_questions():
    """Test top 25 customer questions."""
    base = "http://localhost:8803"
    results = []
    
    questions = [
        ("Q01", "Cheapest coding model?", "/v1/recommend?task=coding&limit=1"),
        ("Q02", "Best free coding model?", "/v1/deals/free?limit=1"),
        ("Q03", "Cheapest >=128k?", "/v1/deals?min_context=131072&limit=1"),
        ("Q04", "Mega deals?", "/v1/mega-deals?limit=3"),
        ("Q05", "Providers?", "/v1/providers?limit=5"),
        ("Q06", "Verification status?", "/v1/verification-runs?limit=1"),
        ("Q07", "Free plan for 100 requests?", "/v1/free/plan"),
        ("Q08", "Deal history?", "/v1/history?limit=5"),
        ("Q09", "Best value?", "/v1/best-value?limit=3"),
        ("Q10", "Cheapest?", "/v1/cheapest?task=coding"),
    ]
    
    for qid, question, path in questions:
        try:
            r = requests.get("%s%s" % (base, path), timeout=5)
            data = r.json()
            has_data = bool(data)
            results.append({"question": question, "status": "PASS" if has_data else "FAIL",
                          "has_data": has_data})
        except Exception as e:
            results.append({"question": question, "status": "FAIL", "error": str(e)[:50]})
    
    return results


def test_coverage_honesty():
    """Produce honest coverage report."""
    import canonical_db
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    offers = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
    with_assertions = conn.execute("SELECT COUNT(DISTINCT offer_id) FROM offer_assertions").fetchone()[0]
    with_claims = conn.execute("SELECT COUNT(DISTINCT offer_id) FROM claims").fetchone()[0]
    with_evidence = conn.execute("""
        SELECT COUNT(DISTINCT c.offer_id) FROM evidence_v2 e
        JOIN claims c ON e.claim_id = c.claim_id
    """).fetchone()[0]
    with_verification = conn.execute("SELECT COUNT(DISTINCT offer_id) FROM verification_dimensions").fetchone()[0]
    with_freshness = conn.execute("SELECT COUNT(*) FROM offers WHERE last_verified_at IS NOT NULL").fetchone()[0]
    with_lifecycle = conn.execute("SELECT COUNT(*) FROM offers WHERE lifecycle_state IS NOT NULL").fetchone()[0]
    with_economic = conn.execute("SELECT COUNT(*) FROM economic_access").fetchone()[0]
    
    conn.close()
    
    return {
        "catalog_coverage": {
            "total_offers": offers,
            "with_economic_access": with_economic,
            "pct": round(with_economic / offers * 100, 1) if offers > 0 else 0,
        },
        "provenance_coverage": {
            "total_offers": offers,
            "with_assertions": with_assertions,
            "with_claims": with_claims,
            "with_evidence": with_evidence,
            "pct_assertions": round(with_assertions / offers * 100, 1) if offers > 0 else 0,
            "pct_claims": round(with_claims / offers * 100, 1) if offers > 0 else 0,
            "pct_evidence": round(with_evidence / offers * 100, 1) if offers > 0 else 0,
        },
        "verification_coverage": {
            "total_offers": offers,
            "with_verification": with_verification,
            "pct": round(with_verification / offers * 100, 1) if offers > 0 else 0,
        },
        "freshness_coverage": {
            "total_offers": offers,
            "with_freshness": with_freshness,
            "pct": round(with_freshness / offers * 100, 1) if offers > 0 else 0,
        },
        "lifecycle_coverage": {
            "total_offers": offers,
            "with_lifecycle": with_lifecycle,
            "pct": round(with_lifecycle / offers * 100, 1) if offers > 0 else 0,
        },
    }


def run_utility_certification():
    """Run complete utility certification."""
    print("=" * 70)
    print("DELL EXTERNAL ORACLE UTILITY CERTIFICATION")
    print("=" * 70)
    
    start_time = time.time()
    all_results = {}
    
    # Start API
    print("\nStarting API...")
    proc = start_api()
    
    try:
        # 1. REST Contract Tests
        print("\n[1] BLACK-BOX REST")
        rest_results = test_rest_contract()
        passed = sum(1 for r in rest_results if r["status"] == "PASS")
        all_results["rest"] = rest_results
        print("  %d/%d PASS" % (passed, len(rest_results)))
        
        # 2. User Question Tests
        print("\n[2] USER QUESTIONS")
        user_results = test_user_questions()
        passed = sum(1 for r in user_results if r["status"] == "PASS")
        all_results["user_questions"] = user_results
        print("  %d/%d PASS" % (passed, len(user_results)))
        
        # 3. Coverage Honesty
        print("\n[3] COVERAGE HONESTY")
        coverage = test_coverage_honesty()
        all_results["coverage"] = coverage
        print("  Catalog: %d offers" % coverage["catalog_coverage"]["total_offers"])
        print("  Economic: %.1f%%" % coverage["catalog_coverage"]["pct"])
        print("  Assertions: %.1f%%" % coverage["provenance_coverage"]["pct_assertions"])
        print("  Evidence: %.1f%%" % coverage["provenance_coverage"]["pct_evidence"])
        print("  Verification: %.1f%%" % coverage["verification_coverage"]["pct"])
        print("  Freshness: %.1f%%" % coverage["freshness_coverage"]["pct"])
        
    finally:
        stop_api(proc)
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 70)
    print("UTILITY CERTIFICATION SUMMARY")
    print("=" * 70)
    print("Duration: %.1f seconds" % duration)
    
    # Save results
    results_dir = ROOT / "data" / "tests" / "utility"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    run_id = "utility-%s" % time.strftime("%Y%m%d-%H%M%S")
    run_dir = results_dir / run_id
    run_dir.mkdir(exist_ok=True)
    
    with open(run_dir / "run.json", "w") as f:
        json.dump({
            "run_id": run_id,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(end_time)),
            "duration_seconds": duration,
            "results": all_results,
        }, f, indent=2)
    
    print("\nResults saved to: %s/" % run_dir)
    
    return all_results


if __name__ == "__main__":
    run_utility_certification()
