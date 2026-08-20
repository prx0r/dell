#!/usr/bin/env python3
"""app/blog_gate.py — Validate Dell blog posts before publishing.

Run: python3 app/blog_gate.py web/src/content/blog/post.md
Exit 0 = PASS, Exit 1 = KILL
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path


GENERIC_FILLER = [
    "choose the right model", "best for your use case", "depending on your",
    "consider using", "it depends", "right model for", "saves you",
    "thousands of dollars", "98% savings", "94% savings",
    "can save you", "find the cheapest", "best value",
]

TIER_A_DOMAINS = [
    "opencode", "openrouter", "anthropic", "openai", "groq", "together",
    "deepinfra", "huggingface", "nvidia", "google", "microsoft", "meta",
]

TIER_B_DOMAINS = [
    "github.com", "arxiv.org", "blog.", "docs.", "changelog",
]


def extract_frontmatter(content: str) -> dict:
    m = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def gate_1_headline_accuracy(title: str, body: str) -> tuple[str, str]:
    numbers = re.findall(r"\d+[xkKmM]?\b", title)
    multipliers = [n for n in numbers if "x" in n.lower()]
    if multipliers:
        return "WARN", f"Title contains multiplier claims {multipliers} — must verify against official source"
    return "PASS", "No unverified multiplier claims in title"


def gate_2_source_evidence(content: str) -> tuple[str, str]:
    urls = re.findall(r"https?://[^\s\)]+", content)
    official = sum(1 for u in urls if any(d in u for d in TIER_A_DOMAINS))
    independent = sum(1 for u in urls if any(d in u for d in TIER_B_DOMAINS))
    if official == 0:
        return "FAIL", f"No official sources found ({len(urls)} URLs total)"
    if independent == 0:
        return "WARN", f"Official sources: {official}, but no independent sources"
    return "PASS", f"Official: {official}, independent: {independent}"


def gate_3_fx_format(body: str) -> tuple[str, str]:
    required = [
        ("verdict", ["verdict", "opening", "tldr", "summary"]),
        ("correction", ["correction", "headline", "corrected"]),
        ("comparison", ["comparison", "table", "|"]),
        ("evidence", ["evidence", "benchmark", "swe-bench", "terminal-bench"]),
        ("routing", ["routing", "architecture", "diagram"]),
        ("escalation", ["escalation", "escalate"]),
        ("uncertainty", ["uncertainty", "may change", "as of", "limited time"]),
    ]
    found = []
    missing = []
    for name, keywords in required:
        if any(kw.lower() in body.lower() for kw in keywords):
            found.append(name)
        else:
            missing.append(name)
    if len(missing) >= 3:
        return "FAIL", f"Missing {len(missing)}/{len(required)} sections: {missing}"
    if missing:
        return "WARN", f"Found {len(found)}/{len(required)} sections, missing: {missing}"
    return "PASS", f"All {len(required)} sections present"


def gate_4_no_filler(body: str) -> tuple[str, str]:
    body_lower = body.lower()
    filler_count = sum(body_lower.count(w) for w in GENERIC_FILLER)
    total_words = len(body.split())
    ratio = filler_count / max(total_words, 1)
    if ratio > 0.03:
        return "FAIL", f"Filler ratio {ratio:.2%} exceeds 30% threshold"
    if ratio > 0.01:
        return "WARN", f"Filler ratio {ratio:.2%} — borderline"
    return "PASS", f"Filler ratio {ratio:.2%}"


def gate_5_freshness(pub_date: str) -> tuple[str, str]:
    try:
        # Handle both date-only and datetime formats, with or without Z
        clean = pub_date.strip().rstrip("Z").replace("+00:00", "")
        if "T" in clean:
            pub = datetime.fromisoformat(clean)
        else:
            pub = datetime.strptime(clean, "%Y-%m-%d")
        # Ensure timezone-aware
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - pub).days
        if age_days > 90:
            return "FAIL", f"Post is {age_days} days old (>90 day limit)"
        if age_days > 30:
            return "WARN", f"Post is {age_days} days old (>30 day warning)"
        return "PASS", f"Post is {age_days} days old"
    except (ValueError, TypeError):
        return "WARN", f"Could not parse date: {pub_date}"


def gate_6_actionability(body: str) -> tuple[str, str]:
    actionable_patterns = [
        r"use .+ for", r"escalat", r"routing", r"recommend",
        r"first for", r"then", r"when .+ fails",
    ]
    matches = sum(1 for p in actionable_patterns if re.search(p, body, re.IGNORECASE))
    if matches < 2:
        return "FAIL", f"Only {matches} actionable patterns found — post describes but does not recommend"
    return "PASS", f"{matches} actionable patterns found"


def gate_7_anti_hype(body: str) -> tuple[str, str]:
    uncertainty_markers = [
        "may change", "limited time", "as of", "could move",
        "uncertainty", "not verified", "community-reported",
        "estimated", "approximately", "subject to",
    ]
    found = [m for m in uncertainty_markers if m.lower() in body.lower()]
    if not found:
        return "FAIL", "No uncertainty preservation — post overstates confidence"
    if len(found) < 2:
        return "WARN", f"Only {len(found)} uncertainty marker: {found}"
    return "PASS", f"{len(found)} uncertainty markers: {found}"


def validate_post(post_path: str) -> bool:
    path = Path(post_path)
    if not path.exists():
        print(f"KILL: File not found: {post_path}")
        return False

    content = path.read_text()
    fm = extract_frontmatter(content)

    # Get body (after frontmatter)
    fm_match = re.search(r"^---\n.*?\n---", content, re.DOTALL)
    body = content[fm_match.end():] if fm_match else content

    title = fm.get("title", "")
    pub_date = fm.get("pubDate", "")

    print(f"{'=' * 60}")
    print(f"GATE REPORT: {path.name}")
    print(f"  Title: {title}")
    print(f"  Date: {pub_date}")
    print(f"{'=' * 60}")

    gates = [
        ("G1 Headline Accuracy", gate_1_headline_accuracy(title, body)),
        ("G2 Source Evidence", gate_2_source_evidence(content)),
        ("G3 fx Format", gate_3_fx_format(body)),
        ("G4 No Filler", gate_4_no_filler(body)),
        ("G5 Freshness", gate_5_freshness(pub_date)),
        ("G6 Actionability", gate_6_actionability(body)),
        ("G7 Anti-Hype", gate_7_anti_hype(body)),
    ]

    killed = False
    for name, (status, detail) in gates:
        icon = "✓" if status == "PASS" else "⚠" if status == "WARN" else "✗"
        print(f"  {icon} {name}: {status} — {detail}")
        if status == "FAIL":
            killed = True

    print(f"{'=' * 60}")
    if killed:
        print(f"RESULT: KILL — {path.name} failed blocking gate(s)")
    else:
        print(f"RESULT: PASS — {path.name} cleared for publishing")
    print(f"{'=' * 60}")

    return not killed


def main():
    if len(sys.argv) < 2:
        # Validate all posts
        blog_dir = Path("web/src/content/blog")
        if not blog_dir.exists():
            print("No blog directory found")
            sys.exit(1)
        posts = sorted(blog_dir.glob("*.md"))
        if not posts:
            print("No blog posts found")
            sys.exit(1)
        all_passed = True
        for post in posts:
            if not validate_post(str(post)):
                all_passed = False
            print()
        sys.exit(0 if all_passed else 1)
    else:
        result = validate_post(sys.argv[1])
        sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
