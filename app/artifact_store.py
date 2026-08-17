"""Content-addressed artifact storage for raw source data.

Stores fetched bytes so evidence can be reproduced.
"""
from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "data" / "artifacts"


def store_artifact(content: bytes, content_type: str = "text/html") -> dict:
    """Store raw artifact content-addressably."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    sha256 = hashlib.sha256(content).hexdigest()
    # Store as gzipped content-addressed file
    path = ARTIFACTS_DIR / f"{sha256[:2]}/{sha256}.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        f.write(content)
    return {
        "artifact_id": sha256,
        "sha256": sha256,
        "uri": f"artifacts/{sha256[:2]}/{sha256}.gz",
        "content_type": content_type,
        "byte_length": len(content),
    }


def load_artifact(artifact_id: str) -> bytes:
    """Load raw artifact by content hash."""
    path = ARTIFACTS_DIR / f"{artifact_id[:2]}/{artifact_id}.gz"
    if not path.exists():
        return b""
    with gzip.open(path, "rb") as f:
        return f.read()


def has_artifact(artifact_id: str) -> bool:
    """Check if artifact exists."""
    return (ARTIFACTS_DIR / f"{artifact_id[:2]}/{artifact_id}.gz").exists()
