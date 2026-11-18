'use strict';
const $ = s => document.querySelector(s);
const icons = {
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 folder:'<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3Z"/>',
 link:'<path d="m10 14 4-4m-5 6-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m0 10a4 4 0 0 0 6 0l4-4a4 4 0 0 0-6-6l-1 1"/>',
 activity:'<path d="M3 12h4l3-8 4 16 3-8h4"/>',
 shield:'<path d="M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7Z"/><path d="m8 12 3 3 5-6"/>',
 cloud:'<path d="M7 18H6a4 4 0 0 1-1-8 7 7 0 0 1 13-1 4.5 4.5 0 0 1 0 9h-1m-5 3V12m-3 3 3-3 3 3"/>',
 lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
 logout:'<path d="M10 4H5v16h5m5-12 4 4-4 4m-6-4h10"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
 file:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Zm0 0v6h6M8 13h8m-8 4h5"/>',
 download:'<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>',
 trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
 copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
 users:'<circle cx="9" cy="7" r="4"/><path d="M2 21v-3a7 7 0 0 1 14 0v3m1-18a4 4 0 0 1 0 8m3 10v-3a6 6 0 0 0-3-5"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">${icons[name] || icons.file}</svg>`;
function hydrateIcons(){document.querySelectorAll('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));}
const esc = text => String(text).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let user, csrf, workspace={files:[],shares:[],events:[]}, view='overview', register=false;
let toastTimer;
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').hidden=true,4200);}
async function api(path,body){
 const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||''},body:JSON.stringify(body)});
 const result=await response.json();
 if(!response.ok){if(response.status===401&&user)showLogin();throw new Error(result.error||'Request failed.');}
 return result;
}
const bytes=n=>n>=1048576?(n/1048576).toFixed(1)+' MB':n>=1024?(n/1024).toFixed(1)+' KB':n+' B';
const date=n=>new Date(n*1000).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
const fullDate=n=>new Date(n*1000).toLocaleString();
function relative(n){const mins=Math.floor((Date.now()/1000-n)/60);return mins<1?'Just now':mins<60?mins+'m ago':mins<1440?Math.floor(mins/60)+'h ago':date(n);}
const active=s=>!s.revoked&&s.expires>Date.now()/1000;
function fileType(name){return /\.(png|jpe?g)$/i.test(name)?'image':/\.(csv|xlsx)$/i.test(name)?'data':'document';}
function showLogin(){user=null;csrf=null;workspace={files:[],shares:[],events:[]};$('#app').hidden=true;$('#login-screen').hidden=false;$('#auth-form').reset();$('#auth-error').textContent='';}
async function enter(result){$('#file-search').value='';$('#type-filter').value='all';$('#test-file-id').value='';$('#test-result').textContent='';user=result.user;csrf=result.csrf;$('#login-screen').hidden=true;$('#app').hidden=false;$('#profile-name').textContent=user.name;$('#profile-avatar').textContent=user.name.split(' ').map(x=>x[0]).join('').slice(0,2);$('#profile-avatar').className='avatar '+(user.id==='user-b'?'lilac':'mint');$('#profile').title='Sign out of '+user.name+'’s workspace';await refresh();setView('overview');}
async function refresh(){workspace=await api('/api/workspace');render();}
const viewCopy={overview:['Overview','YOUR PERSONAL WORKSPACE','A clear space for your best work.','Everything you need, safely in one place.'],files:['My files','YOUR PRIVATE COLLECTION','A home for everything you’re working on.','Upload, organize, and share files with confidence.'],shared:['Shared links','SHARING ON YOUR TERMS','Good work is worth sharing.','Manage the links you create. Stay in control of access.'],activity:['Activity log','YOUR WORKSPACE HISTORY','Every action, accounted for.','Follow uploads, downloads, and security events.'],security:['Security center','PROTECTION AT EVERY STEP','Your files. Your boundaries.','Explore the controls protecting your local workspace.']};
function setView(next){view=next;const c=viewCopy[view];$('#breadcrumb-view').textContent=c[0];$('#page-eyebrow').textContent=c[1];$('#page-title').textContent=c[2];$('#page-subtitle').textContent=c[3];document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));for(const id of ['overview-content','overview-bottom'])$('#'+id).hidden=view!=='overview';$('#files-content').hidden=!['overview','files'].includes(view);for(const v of ['shared','activity','security'])$('#'+v+'-content').hidden=view!==v;$('#upload-button').hidden=!['overview','files'].includes(view);$('#files-title').innerHTML=(view==='files'?'My files':'Recent files')+' <span id="file-count" class="count-badge"></span>';renderFiles();}
function render(){
 const total=workspace.files.reduce((n,f)=>n+f.size,0);
 $('#nav-count').textContent=workspace.files.length;$('#stat-files').textContent=workspace.files.length;$('#stat-storage').textContent=bytes(total);$('#stat-shares').textContent=workspace.shares.filter(active).length;$('#storage-used').textContent=bytes(total)+' of 100 MB used';$('#storage-progress').style.width=Math.min(100,total/1048576)+'%';
 renderFiles();renderShares();$('#recent-activity').innerHTML=renderEvents(workspace.events.slice(0,3));$('#activity-list').innerHTML=renderEvents(workspace.events);hydrateIcons();
}
function renderFiles(){
 const q=$('#file-search').value.toLowerCase(), type=$('#type-filter').value;
 const files=workspace.files.filter(f=>f.name.toLowerCase().includes(q)&&(type==='all'||fileType(f.name)===type));
 $('#file-count').textContent=workspace.files.length;
 $('#file-footer').textContent=`Showing ${files.length} of ${workspace.files.length} files`;
 $('#file-rows').innerHTML=files.length?files.map(f=>`<tr><td><div class="file-name"><span class="file-symbol ${fileType(f.name)}">${icon('file')}</span><span>${esc(f.name)}</span></div></td><td>${bytes(f.size)}</td><td>${date(f.created)}</td><td><span class="access-badge">${icon('lock')} Only you</span></td><td><div class="actions"><button class="icon-button" data-action="download" data-id="${f.id}" title="Download file" aria-label="Download ${esc(f.name)}">${icon('download')}</button><button class="icon-button" data-action="share" data-id="${f.id}" title="Create share link" aria-label="Share ${esc(f.name)}">${icon('link')}</button><button class="icon-button" data-action="copy" data-id="${f.id}" title="Copy file ID for access test" aria-label="Copy file ID">${icon('copy')}</button><button class="icon-button" data-action="delete" data-id="${f.id}" title="Delete file" aria-label="Delete ${esc(f.name)}">${icon('trash')}</button></div></td></tr>`).join(''):'<tr><td colspan="5"><div class="empty">'+(workspace.files.length?'No files match your search.':'Your workspace is ready.<br>Upload your first file to get started.')+'</div></td></tr>';
}
const eventLabels={workspace_created:'Workspace ready',sign_in:'Signed in to workspace',upload:'File uploaded',download:'File downloaded',delete:'File deleted',share_created:'Share link created',share_revoked:'Share link revoked',shared_download:'File downloaded via shared link',access_denied:'Unauthorized access blocked',upload_rejected:'Upload rejected'};
function renderEvents(events){return events.length?events.map(e=>`<div class="event"><span class="event-icon">${icon(e.outcome==='blocked'?'shield':e.action.includes('share')?'link':e.action==='sign_in'?'lock':'file')}</span><div class="event-info"><b>${esc(eventLabels[e.action]||e.action)}</b><small>${esc(e.detail)}</small></div><time title="${esc(fullDate(e.created))}">${relative(e.created)}</time></div>`).join(''):'<div class="empty">No activity yet. Your next step starts the story.</div>';}
function renderShares(){
 $('#share-list').innerHTML=workspace.shares.length?workspace.shares.map(s=>`<div class="share-row"><span class="file-symbol">${icon('link')}</span><div><b>${esc(s.name)}</b><p>${s.revoked?'Revoked':active(s)?'Expires '+fullDate(s.expires):'Expired '+fullDate(s.expires)}</p></div><span class="share-status ${active(s)?'':'inactive'}">${s.revoked?'Revoked':active(s)?'Active':'Expired'}</span>${active(s)?`<button class="secondary" data-revoke="${s.id}">Revoke link</button>`:''}</div>`).join(''):'<div class="empty">No shared links yet.<br>Choose a file and select the link icon to create one.</div>';
}
function modal(html){$('#modal-content').innerHTML=html;$('#modal').showModal();}
async function copyText(value){try{await navigator.clipboard.writeText(value);toast('Copied to clipboard.');}catch{modal('<h2>Copy this value</h2><p>Select and copy the value below.</p><div class="share-url">'+esc(value)+'</div>');}}
async function downloadFile(id){const r=await fetch('/api/files/'+encodeURIComponent(id)+'/download');if(!r.ok){let data=await r.json();throw new Error(data.error);}const blob=await r.blob();const name=workspace.files.find(f=>f.id===id)?.name||'download';const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);await refresh();}
async function uploadFiles(files){
 if(!files.length)return;
 $('#upload-button').disabled=true;let uploaded=0;
 try{for(const file of files){if(!file.size||file.size>10*1024*1024)throw new Error(file.name+': choose a nonempty file up to 10 MB.');const content=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Unable to read file.'));reader.readAsDataURL(file);});await api('/api/upload',{name:file.name,content});uploaded++;}toast(uploaded+' file'+(uploaded===1?'':'s')+' uploaded.');}catch(e){toast((uploaded?uploaded+' uploaded. ':'')+e.message);}finally{$('#upload-button').disabled=false;$('#file-input').value='';await refresh();}
}
$('#auth-form').addEventListener('submit',async e=>{e.preventDefault();$('#auth-error').textContent='';$('#auth-submit').disabled=true;try{const fields=Object.fromEntries(new FormData(e.target));await enter(await api(register?'/api/register':'/api/login',fields));}catch(e){$('#auth-error').textContent=e.message;}finally{$('#auth-submit').disabled=false;}});
document.querySelectorAll('[data-demo]').forEach(button => button.addEventListener('click', () => {
  $('#auth-form [name=email]').value = button.dataset.demo === 'a' ? 'alex@vaultspace.demo' : 'jamie@vaultspace.demo';
  $('#auth-form [name=password]').focus();
}));
$('#auth-toggle').onclick=()=>{register=!register;$('#name-field').hidden=!register;$('#name-field input').required=register;$('#auth-title').textContent=register?'Make space for your work':'Welcome to your workspace';$('#auth-subtitle').textContent=register?'Create your private account to get started.':'Sign in to keep your work moving.';$('#auth-submit').textContent=register?'Create account →':'Sign in →';$('#auth-toggle').textContent=register?'Sign in':'Create an account';$('#auth-prompt').textContent=register?'Already have an account?':'New here?';$('#auth-form [name=password]').minLength=register?12:1;$('#auth-form [name=password]').autocomplete=register?'new-password':'current-password';$('#auth-error').textContent='';};
async function logout(){try{await api('/api/logout',{});showLogin();}catch(e){toast(e.message);}}
$('#logout').onclick=logout;$('#profile').onclick=logout;
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
$('#security-shortcut').onclick=()=>setView('security');$('#view-activity').onclick=()=>setView('activity');$('#refresh-activity').onclick=()=>refresh().catch(e=>toast(e.message));
$('#upload-button').onclick=()=>$('#file-input').click();$('#file-input').onchange=e=>uploadFiles([...e.target.files]);$('#file-search').oninput=renderFiles;$('#type-filter').onchange=renderFiles;
$('#file-rows').onclick=async e=>{const b=e.target.closest('[data-action]');if(!b)return;const f=workspace.files.find(x=>x.id===b.dataset.id);try{
 if(b.dataset.action==='download')await downloadFile(f.id);
 if(b.dataset.action==='copy')await copyText(f.id);
 if(b.dataset.action==='delete'){
  modal(`<span class="stat-icon peach">${icon('trash')}</span><h2>Delete this file?</h2><p>${esc(f.name)} will be permanently removed from this local workspace. Its shared links will stop working.</p><div class="modal-actions"><button id="cancel-delete" class="secondary">Keep file</button><button id="confirm-delete" class="primary danger">Delete file</button></div>`);
  $('#cancel-delete').onclick=()=>$('#modal').close();$('#confirm-delete').onclick=async()=>{try{await api('/api/delete',{file_id:f.id});$('#modal').close();await refresh();toast('File deleted.');}catch(e){toast(e.message);}};
 }
 if(b.dataset.action==='share'){
  modal(`<span class="stat-icon lavender">${icon('link')}</span><h2>A link, on your terms.</h2><p>Share <b>${esc(f.name)}</b> with a temporary download link. Anyone with the link can download this file.</p><label>Link expires in<select id="share-expiry"><option value="1">1 minute · Quick demo</option><option value="15">15 minutes</option><option value="60" selected>1 hour</option><option value="1440">24 hours</option></select></label><button id="create-link" class="primary">Create secure link →</button>`);
  $('#create-link').onclick=async()=>{const b=$('#create-link');b.disabled=true;try{const result=await api('/api/share',{file_id:f.id,minutes:Number($('#share-expiry').value)});const url=location.origin+result.path;$('#modal-content').innerHTML=`<span class="stat-icon green">${icon('link')}</span><h2>Ready to share.</h2><p>Expires ${esc(fullDate(result.expires))}. Copy this link now; the full link is only displayed once.</p><div class="share-url">${esc(url)}</div><button class="primary" id="copy-share">Copy link ${icon('copy')}</button><p>You can revoke it anytime from Shared links.</p>`;$('#copy-share').onclick=()=>copyText(url);await refresh();}catch(e){b.disabled=false;toast(e.message);}};
 }
 }catch(e){toast(e.message);}};
$('#share-list').onclick=e=>{const b=e.target.closest('[data-revoke]');if(!b)return;modal('<h2>Revoke this link?</h2><p>Anyone using this link will lose access immediately.</p><div class="modal-actions"><button id="cancel-revoke" class="secondary">Keep link</button><button id="confirm-revoke" class="primary">Revoke link</button></div>');$('#cancel-revoke').onclick=()=>$('#modal').close();$('#confirm-revoke').onclick=async()=>{try{await api('/api/revoke',{share_id:b.dataset.revoke});$('#modal').close();await refresh();toast('Link revoked.');}catch(e){toast(e.message);}};};
$('#access-test').onsubmit=async e=>{e.preventDefault();const id=$('#test-file-id').value.trim();const r=await fetch('/api/files/'+encodeURIComponent(id)+'/download');const out=$('#test-result');if(r.status===404){out.textContent='Access denied. If this is an existing file from the other user, the ownership check worked. Confirm the ID in that user’s workspace.';out.className='test-pass';}else if(r.ok){out.textContent='Access allowed: this file belongs to the current account. Use the other user’s file ID to demonstrate isolation.';out.className='test-fail';}else{out.textContent='Test could not complete. Sign in again and retry.';out.className='test-fail';}await refresh();};
$('#controls').innerHTML=[['Session authentication','HttpOnly, SameSite cookies; sessions expire after 8 hours.'],['Ownership authorization','Every private file operation checks the signed-in owner.'],['Password hashing','PBKDF2-SHA256 with per-user salts and 600,000 iterations.'],['Upload restrictions','File extension allowlist, 10 MB per file, 100 MB per user. File contents are not malware-scanned.'],['Expiring, revocable links','Random bearer tokens; hashes stored in the database.'],['Request protection','CSRF tokens, same-origin checks, and security headers.'],['Audit trail','Account-scoped server logs of file and security actions.']].map(([a,b])=>`<div class="control"><span>✓</span><div><b>${a}</b><p>${b}</p></div></div>`).join('');
let dragDepth=0;document.addEventListener('dragenter',e=>{if(user&&e.dataTransfer.types.includes('Files')){e.preventDefault();dragDepth++;document.body.classList.add('drop-active');}});document.addEventListener('dragleave',()=>{if(--dragDepth<=0){dragDepth=0;document.body.classList.remove('drop-active');}});document.addEventListener('dragover',e=>{if(user)e.preventDefault();});document.addEventListener('drop',e=>{e.preventDefault();dragDepth=0;document.body.classList.remove('drop-active');if(user)uploadFiles([...e.dataTransfer.files]);});
setInterval(()=>{if(user){renderShares();$('#stat-shares').textContent=workspace.shares.filter(active).length;}},15000);
hydrateIcons();api('/api/session').then(enter).catch(()=>showLogin());
