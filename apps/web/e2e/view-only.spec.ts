import {test,expect} from '@playwright/test';

test('shared member reads PDF but cannot download; revocation blocks preview',async({browser,baseURL},info)=>{
 test.setTimeout(240000);
 const owner=await browser.newContext({baseURL}),reader=await browser.newContext({baseURL});
 const suffix=Date.now()+'-'+Math.random().toString(16).slice(2);
 const email=`view-owner-${suffix}@example.test`,member=`view-member-${suffix}@example.test`,password='view-only-test-password';
 const origin=new URL(baseURL!).origin;
 const post=async(context:typeof owner,path:string,csrf:string,data:unknown)=>{
  const r=await context.request.post('/api'+path,{headers:{Origin:origin,'X-CSRF-Token':csrf},data});expect(r.ok()).toBeTruthy();return r.json();
 };
 try{
  const auth=await post(owner,'/auth/register','',{email,password});
  await post(owner,'/workspace/members',auth.csrf,{email:member,password});
  const b=await post(reader,'/auth/login','',{email:member,password});
  // A real one-page PDF generated from local strings, with valid byte offsets.
  const stream='BT /F1 18 Tf 30 100 Td (View only demonstration) Tj ET';
  const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',`<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`];
  let pdf='%PDF-1.4\n';const offsets=[0];
  for(let i=0;i<objects.length;i++){offsets.push(Buffer.byteLength(pdf));pdf+=`${i+1} 0 obj\n${objects[i]}\nendobj\n`;}
  const xref=Buffer.byteLength(pdf);pdf+='xref\n0 6\n0000000000 65535 f \n'+offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')+`trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  const upload=await owner.request.post('/api/files',{headers:{Origin:origin,'X-CSRF-Token':auth.csrf},multipart:{file:{name:'view-only-demo.pdf',mimeType:'application/pdf',buffer:Buffer.from(pdf)}},timeout:100000});
  expect(upload.ok()).toBeTruthy();const version=await upload.json();
  const download=`/api/files/${version.file_id}/versions/${version.id}/download`,preview=download.replace('/download','/preview');
  expect((await reader.request.get(preview)).status()).toBe(403);
  await post(owner,`/files/${version.file_id}/share`,auth.csrf,{email:member});
  await expect.poll(async()=>{const r=await owner.request.get(`/api/files/${version.file_id}`);return (await r.json()).versions[0].status},{timeout:180000,intervals:[2000,5000]}).toBe('APPROVED');
  expect((await reader.request.get(download)).status()).toBe(403);
  expect((await reader.request.get(preview)).status()).toBe(200);
  const page=await reader.newPage();const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/files');await page.getByRole('button',{name:/view-only-demo.pdf/}).first().click();
  const dialog=page.getByRole('dialog');
  await expect(dialog.getByRole('button',{name:'Download current version'})).toHaveCount(0);
  await dialog.getByRole('button',{name:'Open file (view only)',exact:true}).click();
  await expect(dialog.getByText('Page 1 of 1',{exact:true})).toBeVisible({timeout:20000});
  await expect.poll(()=>dialog.locator('canvas').evaluate(c=>(c as HTMLCanvasElement).width)).toBeGreaterThan(0);
  await expect(dialog.getByRole('alert')).toHaveCount(0);
  await page.screenshot({path:info.outputPath('view-only-reader.png'),fullPage:true});
  const revoked=await owner.request.delete(`/api/files/${version.file_id}/share/${b.user.id}`,{headers:{Origin:origin,'X-CSRF-Token':auth.csrf}});expect(revoked.ok()).toBeTruthy();
  expect((await reader.request.get(preview)).status()).toBe(403);
  expect((await reader.request.get(download)).status()).toBe(403);
  await expect(dialog.locator('canvas')).toHaveCount(0,{timeout:15000});
  expect(errors).toEqual([]);
 }finally{await owner.close();await reader.close();}
});
