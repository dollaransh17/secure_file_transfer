"""Synthetic UI fixture, not neural inference or a malware detector."""
def result(version):
    # Stable arbitrary display scores. No model, file parsing or threat verdict.
    score = int(version.digest[:8], 16) % 101
    return dict(mode='mock', model='mock-cnn-demo-v1', release_authority=False,
                demo_scores={'demo_class_a': score, 'demo_class_b': 100-score},
                digest=version.digest, object_version=version.object_version,
                generation=version.generation,
                explanation='Synthetic scores derived from the recorded fingerprint. No CNN was run. Not malware probabilities.')


def record(db, version):
    from .db import Event
    db.add(Event(tenant_id=version.tenant_id,file_id=version.file_id,version_id=version.id,
                 kind='MOCK_CNN_ANALYSIS',details=result(version)))
