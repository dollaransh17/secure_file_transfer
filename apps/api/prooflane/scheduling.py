"""Ordering only; never modifies scan, evidence, ACL or release state."""
from dataclasses import dataclass

@dataclass
class Candidate:
    id: str
    tenant: str
    created: float
    deadline: float
    cost: float
    attempts: int = 0

def rank(candidates, strategy, at, predictions=None, starvation=120):
    predictions=predictions or {}
    def key(j):
        # Deadline urgency and bounded starvation override any workload prediction.
        hard = 0 if j.deadline<=at+max(1,j.cost) else 1 if at-j.created>=starvation else 2
        if strategy=='fifo': utility=j.created
        elif strategy=='edf': utility=j.deadline
        elif strategy=='rule': utility=j.deadline - 10*(at-j.created)/max(1,j.cost) + 5*j.attempts
        elif strategy in ('lightgbm','tgn'):
            duration,demand=predictions[j.id]
            utility=-((1+max(0,demand))/max(.01,duration))
        else: raise ValueError('Unknown strategy')
        return (hard, j.deadline if hard==0 else j.created if hard==1 else utility,j.created,j.id)
    return sorted(candidates,key=key)
