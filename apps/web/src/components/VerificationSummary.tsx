type Scan={version_id:string,result:string,engine:string,created:number,expires:number};
type Integrity={version_id:string,valid:boolean,expires:number};
export function VerificationSummary({version,scans,integrity}:{version:{id:string,status:string},scans:Scan[],integrity:Integrity[]}){
 const scan=scans.filter(s=>s.version_id===version.id).at(-1);
 const check=integrity.filter(i=>i.version_id===version.id).at(-1);
 const expires=scan&&check?Math.min(scan.expires,check.expires):null;
 const expired=expires!==null&&expires<=Date.now()/1000;
 return <section className="storage-location" aria-label="Verification summary">
  <h3>File verification</h3>
  <p><strong>{version.status.toLowerCase().replaceAll('_',' ')}</strong>{expired?' · Evidence expired':''}</p>
  <dl className="details">
   <dt>Antivirus result</dt><dd>{scan?.result||'Awaiting scan'}</dd>
   <dt>Integrity check</dt><dd>{check?(check.valid?'Matched':'Mismatch'):'Awaiting verification'}</dd>
   <dt>Scanner / signatures</dt><dd>{scan?.engine||'Not yet recorded'}</dd>
   <dt>Evidence expires</dt><dd>{expires?new Date(expires*1000).toLocaleString():'Not yet recorded'}</dd>
  </dl>
  <p className="muted">Approval requires clean antivirus evidence and matching integrity checks. These results do not provide a numerical probability that the file is safe.</p>
 </section>;
}
