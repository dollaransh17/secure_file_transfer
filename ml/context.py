"""Shared, dependency-free causal graph input contract for export/train/serve."""
import math

INPUT_SCHEMA = 2
MAX_EVENTS = 128
NODE_TYPES = {'user': 0, 'file': 1, 'version': 2, 'scan': 3, 'integrity': 4, 'job': 5, 'policy': 6}
EDGE_TYPES = ['USER_UPLOADED_FILE', 'USER_REQUESTED_FILE', 'USER_SHARED_FILE',
              'FILE_HAS_VERSION', 'VERSION_HAS_SCAN', 'VERSION_HAS_INTEGRITY',
              'POLICY_GOVERNS_SCAN', 'JOB_VERIFIES_VERSION', 'USER_PERMISSION_REVOKED']

def node_type(node):
    kind, separator, identity = node.partition(':')
    if not separator or not identity or kind not in NODE_TYPES:
        raise ValueError('Unknown typed graph node')
    return NODE_TYPES[kind]

def event_vector(features):
    """Eight permitted event attributes; labels and arbitrary metadata excluded."""
    size = max(0, float(features.get('size', 0)))
    epoch = max(0, float(features.get('epoch', 0)))
    values = [math.log1p(size), float(features.get('authorized') is True),
              float(features.get('valid') is True), float(features.get('result') == 'CLEAN'),
              float(features.get('result') == 'INFECTED'), math.log1p(epoch), 0., 0.]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Non-finite graph features')
    return values

def encode_event(source, target, timestamp, edge, features=None, identity=''):
    if edge not in EDGE_TYPES or not math.isfinite(timestamp):
        raise ValueError('Invalid graph event')
    return {'id': identity, 'src': source, 'dst': target, 'time': timestamp,
            'edge': EDGE_TYPES.index(edge), 'src_type': node_type(source),
            'dst_type': node_type(target), 'x': event_vector(features or {})}

def snapshot(events, at):
    """Never admit same-time or future events; ordering is stable for timestamp ties."""
    past = [e for e in events if e['time'] < at]
    past.sort(key=lambda e: (e['time'], e.get('id', ''), e['src'], e['dst']))
    selected = past[-MAX_EVENTS:]
    validate_context(selected, at)
    return selected

def validate_context(events, at):
    if len(events) > MAX_EVENTS:
        raise ValueError('Graph context exceeds the common replay bound')
    previous = float('-inf')
    for event in events:
        if not math.isfinite(event['time']) or event['time'] >= at or event['time'] < previous:
            raise ValueError('Graph context is not strictly historical and chronological')
        if node_type(event['src']) != event['src_type'] or node_type(event['dst']) != event['dst_type']:
            raise ValueError('Graph node type mismatch')
        if event['edge'] not in range(len(EDGE_TYPES)):
            raise ValueError('Unknown graph edge type')
        if len(event['x']) != 8 or not all(math.isfinite(float(v)) for v in event['x']):
            raise ValueError('Invalid graph event vector')
        previous = event['time']
