import {useState} from 'react';
type Result={model:string,demo_scores:Record<string,number>,explanation:string};
export function CnnDemo({result,run,verification}:{result:Result|null,run?:()=>Promise<void>,verification?:string}){
 const [busy,setBusy]=useState(false);
 const score=result?Math.max(0,Math.min(100,result.demo_scores.demo_class_a??0)):0;
 return <section className="storage-location" aria-label="CNN analysis">
  <p><strong>ByteCNN analysis</strong> <span className="badge">Simulated</span></p>
  {result?<div className="cnn-preview">
   <span className="eyebrow">DEMO SCORE</span><strong className="cnn-preview-score">{score}%</strong>
   <meter min={0} max={100} value={score} aria-label="Simulated ByteCNN demo score"/>
   <p className="muted">Illustrative percentage, not a security rating.</p>
   <h3>Analysis summary</h3>
   <p>ByteCNN result preview generated for this file version. The score is repeatable for the same file fingerprint.</p>
   <div className="notice">Recorded verification: <strong>{verification?.toLowerCase().replaceAll('_',' ')||'unavailable'}</strong>. Approval follows ClamAV and integrity checks.</div>
  </div>:<p>No analysis recorded for this version yet.</p>}
  {run&&!result&&<p><button disabled={busy} aria-busy={busy} onClick={async()=>{if(busy)return;setBusy(true);try{await run()}finally{setBusy(false)}}}>{busy?'Generating…':'Generate analysis'}</button></p>}
 </section>;
}
