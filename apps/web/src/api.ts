export let csrf='';
export function setCsrf(value:string){csrf=value}
let expiredHandler:(()=>void)|undefined;
export function onSessionExpired(handler:()=>void){expiredHandler=handler;return()=>{if(expiredHandler===handler)expiredHandler=undefined}}
export function handleUnauthorized(path:string,requestCsrf:string){
 // Ignore public auth failures and responses belonging to an earlier session.
 // Logout owns its own redirect; a failed login must retain its form error.
 if(['/auth/login','/auth/register','/auth/logout'].includes(path)||!requestCsrf||csrf!==requestCsrf)return;
 setCsrf('');expiredHandler?.();
}
export class ApiError extends Error {constructor(public status:number,message:string){super(message)}}
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const requestCsrf=csrf;
 const response=await fetch('/api'+path,{...options,credentials:'include',headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),'X-CSRF-Token':requestCsrf,...options.headers}});
 if(response.status===401)handleUnauthorized(path,requestCsrf);
 if(!response.ok){const data=await response.json().catch(()=>({detail:response.statusText}));throw new ApiError(response.status,typeof data.detail==='string'?data.detail:'Please check the supplied fields')}
 return response.json();
}
export function upload(file:File,fileId:string|undefined,onProgress:(n:number)=>void){return new Promise<void>((resolve,reject)=>{
 const requestCsrf=csrf;
 const xhr=new XMLHttpRequest();xhr.open('POST','/api/files'+(fileId?'?file_id='+fileId:''));xhr.withCredentials=true;xhr.setRequestHeader('X-CSRF-Token',requestCsrf);
 xhr.upload.onprogress=e=>{if(e.lengthComputable)onProgress(Math.round(100*e.loaded/e.total))};
 xhr.onload=()=>{
  if(xhr.status>=200&&xhr.status<300){resolve();return}
  if(xhr.status===401)handleUnauthorized('/files',requestCsrf);
  let message='Upload failed';try{const detail=JSON.parse(xhr.responseText).detail;if(typeof detail==='string')message=detail}catch{message=xhr.statusText||message}
  reject(new Error(message));
 };xhr.onerror=()=>reject(new Error('Connection interrupted'));
 const data=new FormData();data.append('file',file);xhr.send(data);
})}
export const bytes=(value:number)=>value<1024?value+' B':value<1048576?(value/1024).toFixed(1)+' KB':(value/1048576).toFixed(1)+' MB';
export const date=(value:number|null)=>value?new Date(value*1000).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'—';
export const words=(s:string)=>s.toLowerCase().replaceAll('_',' ');
