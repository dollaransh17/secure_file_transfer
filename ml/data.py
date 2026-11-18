"""Shared temporal restrictions and prediction-time tabular features."""
import json
from pathlib import Path
FEATURES=['log_size','age','deadline_remaining','previous_duration','recent_authorized_demand','queue_length','attempts','worker_capacity']
HORIZON=300

def load(path):
    rows=[json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    rows.sort(key=lambda r:r['time'])
    for row in rows:
        if row['history_until']>=row['time']: raise ValueError('Future or simultaneous event feature leakage')
        if len(row['x'])!=len(FEATURES): raise ValueError('Feature schema mismatch')
        import math
        if not all(math.isfinite(float(v)) for v in row['x']): raise ValueError('Non-finite features')
        if 'context' in row:
            from ml.context import validate_context
            validate_context(row['context'],row['time'])
            if any(e['time']>row['history_until'] for e in row['context']):raise ValueError('Context exceeds declared observation cutoff')
    return rows

def split(rows):
    if len(rows)<3: raise ValueError('At least three temporal records are required')
    a=rows[int(len(rows)*.6)]['time'];b=rows[int(len(rows)*.8)]['time']
    # Purge targets whose future demand window crosses a split boundary.
    return ([r for r in rows if max(r['time']+HORIZON,r.get('target_end',0))<a],
            [r for r in rows if a<=r['time'] and max(r['time']+HORIZON,r.get('target_end',0))<b],
            [r for r in rows if r['time']>=b])

def features(size,at,created,deadline,previous,recent,queue,attempts,capacity):
    import math
    return [math.log1p(size),max(0,at-created)/300,(deadline-at)/300,previous,recent,queue,attempts,capacity]
