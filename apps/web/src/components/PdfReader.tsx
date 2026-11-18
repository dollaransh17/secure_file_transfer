import {useEffect,useRef,useState} from 'react';
import {getDocument,GlobalWorkerOptions,type PDFDocumentProxy} from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
GlobalWorkerOptions.workerSrc=workerUrl;
export function PdfReader({blob}:{blob:Blob}){
 const canvas=useRef<HTMLCanvasElement>(null);
 const [pdf,setPdf]=useState<PDFDocumentProxy|null>(null),[page,setPage]=useState(1),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{
  let cancelled=false;let task:ReturnType<typeof getDocument>|undefined;
  setPdf(null);setPage(1);setError('');
  blob.arrayBuffer().then(data=>{if(cancelled)return;task=getDocument({data});return task.promise}).then(doc=>{if(doc&&!cancelled)setPdf(doc)}).catch(e=>{if(!cancelled)setError('Unable to open this PDF: '+e.message)});
  return()=>{cancelled=true;void task?.destroy()};
 },[blob]);
 useEffect(()=>{
  if(!pdf||!canvas.current)return;
  let cancelled=false;let renderTask:ReturnType<Awaited<ReturnType<PDFDocumentProxy['getPage']>>['render']>|undefined;
  setBusy(true);setError('');
  pdf.getPage(page).then(p=>{
   if(cancelled||!canvas.current)return;
   const viewport=p.getViewport({scale:Math.min(1.4,1200/p.getViewport({scale:1}).width)});
   const target=canvas.current;target.width=Math.ceil(viewport.width);target.height=Math.ceil(viewport.height);
   const context=target.getContext('2d');if(!context)throw new Error('Canvas unavailable');
   renderTask=p.render({canvas:target,canvasContext:context,viewport});return renderTask.promise;
  }).catch(e=>{if(!cancelled)setError('Unable to render page: '+e.message)}).finally(()=>{if(!cancelled)setBusy(false)});
  return()=>{cancelled=true;renderTask?.cancel()};
 },[pdf,page]);
 return <section className="pdf-reader" aria-label="PDF view-only reader"><div className="actions"><button disabled={!pdf||page<=1||busy} onClick={()=>setPage(n=>n-1)}>Previous page</button><span aria-live="polite">{pdf?`Page ${page} of ${pdf.numPages}`:'Loading PDF…'}</span><button disabled={!pdf||page>=pdf.numPages||busy} onClick={()=>setPage(n=>n+1)}>Next page</button></div>{error&&<p role="alert">{error}</p>}<canvas ref={canvas} aria-label={`PDF page ${page}`} style={{maxWidth:'100%',height:'auto',display:'block',margin:'16px auto'}}/></section>
}
