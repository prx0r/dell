"""Adapter contract for Oracle-1.

Every adapter should return:
- FetchResult
- Observation
- RawArtifact
- ExtractedAssertion[]
- NegativeObservation[]
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FetchResult:
    """Result of fetching from a source."""
    success: bool
    url: str
    status_code: int
    content: bytes
    content_type: str
    headers: dict
    fetched_at: str
    error: Optional[str] = None


@dataclass
class Observation:
    """Observation from a source."""
    source_id: str
    url: str
    fetched_at: str
    status_code: int
    content_hash: str
    model_count: int = 0
    metadata: dict = None


@dataclass
class RawArtifact:
    """Content-addressed raw artifact."""
    artifact_id: str
    content: bytes
    content_type: str
    sha256: str
    source_url: str
    retrieved_at: str


@dataclass
class ExtractedAssertion:
    """Assertion extracted from observation."""
    offer_id: str
    field: str
    value: str
    confidence: float
    source_url: str
    observation_id: Optional[int] = None
    claim_id: Optional[int] = None


@dataclass
class NegativeObservation:
    """Record of something NOT found."""
    model_id: str
    field: str
    absence_type: str  # MODEL_ABSENT, FIELD_ABSENT, PRICE_ABSENT, etc.
    source_url: str
    checked_at: str
    details: Optional[str] = None


class AdapterContract:
    """Base class for adapters with Oracle-1 contract."""
    
    def __init__(self, source_id: str):
        self.source_id = source_id
    
    def fetch(self) -> FetchResult:
        """Fetch from source."""
        raise NotImplementedError
    
    def extract(self, observation: Observation) -> List[ExtractedAssertion]:
        """Extract assertions from observation."""
        raise NotImplementedError
    
    def find_absences(self, observation: Observation) -> List[NegativeObservation]:
        """Find things that are NOT present."""
        return []
    
    def store_artifact(self, fetch_result: FetchResult) -> RawArtifact:
        """Store raw artifact content-addressably."""
        import hashlib
        sha256 = hashlib.sha256(fetch_result.content).hexdigest()
        return RawArtifact(
            artifact_id=sha256,
            content=fetch_result.content,
            content_type=fetch_result.content_type,
            sha256=sha256,
            source_url=fetch_result.url,
            retrieved_at=fetch_result.fetched_at,
        )
