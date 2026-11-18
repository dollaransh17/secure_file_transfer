type Version={storage_key:string,object_version:string,number:number};
type Location={backend:string,bucket:string|null,region:string|null,aws_console:boolean};

export function StorageLocation({name,version,location}:{name:string,version:Version,location:Location}){
 const s3=location.backend==='s3'&&location.bucket;
 const uri=s3?`s3://${location.bucket}/${version.storage_key}`:null;
 const consoleUrl=s3&&location.aws_console&&location.region?
  `https://s3.console.aws.amazon.com/s3/object/${encodeURIComponent(location.bucket!)}?${new URLSearchParams({region:location.region,prefix:version.storage_key,versionId:version.object_version})}`:null;
 return <section className="storage-location" aria-label="File storage location">
  <p>Your file name stays <strong>{name}</strong> in Prooflane. {s3?'In object storage, this version uses the object key below.':'This installation uses local development storage.'}</p>
  <dl className="details">
   <dt>Prooflane file name</dt><dd>{name}</dd>
   <dt>File version</dt><dd>v{version.number}</dd>
   {s3&&<><dt>S3 bucket</dt><dd className="mono digest">{location.bucket}</dd><dt>AWS region</dt><dd>{location.region}</dd></>}
   <dt>{s3?'S3 object key':'Storage key'}</dt><dd className="mono digest">{version.storage_key}</dd>
   {uri&&<><dt>S3 URI</dt><dd className="mono digest">{uri}</dd></>}
   <dt>Object version ID</dt><dd className="mono digest">{version.object_version}</dd>
  </dl>
  {consoleUrl&&<p><a className="button" href={consoleUrl} target="_blank" rel="noopener noreferrer">View this version in AWS S3</a></p>}
  {consoleUrl&&<p className="muted">Requires your own AWS console permissions. This link does not grant access to the file.</p>}
 </section>;
}
