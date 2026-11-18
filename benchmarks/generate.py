"""Harmless, explicitly synthetic workload targets, not measured scanner timings."""
import argparse,json,random,math,hashlib
from pathlib import Path
SCENARIOS=['new_version_pending','delayed_scan','revocation','duplicate','out_of_order','scanner_timeout','worker_crash','expiry','policy_change','simultaneous_downloads','queue_load','popularity_shift','congestion','concurrent_versions','cross_tenant','integrity_mismatch','unsupported','late_policy_result','retry_exhaustion','starvation']

def harmless_pdf(text):
    # Minimal PDF with computed xref offsets; harmless generated text only.
    content=f'BT /F1 16 Tf 40 780 Td ({text}) Tj ET'.encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream']
    data=bytearray(b'%PDF-1.4\n');offsets=[0]
    for n,obj in enumerate(objects,1):
        offsets.append(len(data));data.extend(f'{n} 0 obj\n'.encode()+obj+b'\nendobj\n')
    xref=len(data);data.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for offset in offsets[1:]:data.extend(f'{offset:010d} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(data)

def generate(output,seed=17,files=200,schedules=10):
    rng=random.Random(seed);out=Path(output);out.mkdir(parents=True,exist_ok=True);fixtures=out/'fixtures';fixtures.mkdir(exist_ok=True)
    for i in range(files):
        ext=['txt','csv','json','pdf','png'][i%5];p=fixtures/f'harmless-{i}.{ext}'
        if ext=='txt': p.write_text(f'Prooflane harmless fixture {i}\n')
        elif ext=='csv': p.write_text(f'id,value\n{i},{rng.random()}\n')
        elif ext=='json': p.write_text(json.dumps({'id':i,'synthetic':True}))
        elif ext=='pdf':
            p.write_bytes(harmless_pdf(f'Prooflane harmless fixture {i}'))
        else:
            from PIL import Image
            Image.new('RGB',(32,32),(i%255,100,150)).save(p)
    from benchmarks.workload import build
    rows=build(seed=seed,files=files)
    (out/'workload.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    scenarios=[{'template':template,'seed':seed+n,'file':n%files} for template in SCENARIOS for n in range(schedules)]
    (out/'scenarios.json').write_text(json.dumps(scenarios,indent=2))
    (out/'manifest.json').write_text(json.dumps({'seed':seed,'files':files,'templates':len(SCENARIOS),'schedules':schedules,'dataset_sha256':hashlib.sha256((out/'workload.jsonl').read_bytes()).hexdigest(),'provenance':'synthetic-v2 causal lifecycle data','input_schema':2},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='artifacts/dataset');p.add_argument('--seed',type=int,default=17);p.add_argument('--files',type=int,default=200);p.add_argument('--schedules',type=int,default=10);a=p.parse_args();generate(a.output,a.seed,a.files,a.schedules)
