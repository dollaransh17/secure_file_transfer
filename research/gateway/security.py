"""All authorization and evidence checks live outside the learned scheduler."""
from dataclasses import dataclass
from time import time as now

@dataclass(frozen=True)
class ReleaseFacts:
    authorized: bool
    target_matches: bool
    status: str
    scan_clean: bool
    scan_bound: bool
    policy_matches: bool
    integrity_matches: bool
    evidence_expires: float

def release_denial(f: ReleaseFacts, at: float | None = None) -> str | None:
    if not f.authorized: return 'Access denied'
    if not f.target_matches: return 'Version is not the current authorized target'
    if f.status != 'APPROVED': return 'Version has not been approved'
    if not f.scan_clean or not f.scan_bound: return 'Exact-version scan evidence required'
    if not f.policy_matches: return 'Scanner policy changed'
    if not f.integrity_matches: return 'Integrity verification required'
    if f.evidence_expires <= (now() if at is None else at): return 'Security evidence expired'
    return None
