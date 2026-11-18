export function CnnPlaceholder({digest}:{digest:string}){
 // Stable illustrative value per file; never consumed by security decisions.
 const value=90+(Number.parseInt(digest.slice(0,8),16)||0)%11;
 return <section className="storage-location" aria-label="CNN placeholder result">
  <h3>CNN result preview</h3>
  <span className="badge">Placeholder</span>
  <div className="cnn-preview"><span className="eyebrow">PREVIEW SCORE</span>
   <strong className="cnn-preview-score">{value}%</strong>
   <meter min={0} max={100} value={value} aria-label="Illustrative confidence"/>
  </div>
 </section>;
}
