import {test,expect,type Page} from '@playwright/test';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {registerWorkspace} from './support';
const diagnostics=new WeakMap<Page,{pageErrors:string[],consoleErrors:string[],cspViolations:string[],authResponses:{path:string,status:number}[],mutations:{path:string,method:string,status:number}[],detailReads:{path:string,status:number,elapsedMs:number}[],requestFailures:{path:string,error:string}[]}>();
test.beforeEach(async({page})=>{
 const data={pageErrors:[] as string[],consoleErrors:[] as string[],cspViolations:[] as string[],authResponses:[] as {path:string,status:number}[],mutations:[] as {path:string,method:string,status:number}[],detailReads:[] as {path:string,status:number,elapsedMs:number}[],requestFailures:[] as {path:string,error:string}[]};
 diagnostics.set(page,data);
 page.on('pageerror',error=>data.pageErrors.push(error.message));
 page.on('console',message=>{if(message.type()==='error'){const text=message.text().slice(0,1500);if(data.consoleErrors.length<50)data.consoleErrors.push(text);if(text.includes('Content Security Policy'))data.cspViolations.push(text);}});
 page.on('response',response=>{
  const path=new URL(response.url()).pathname;
  if(path.startsWith('/api/auth/'))data.authResponses.push({path,status:response.status()});
  const method=response.request().method();
  if(path.startsWith('/api/')&&['POST','PATCH','DELETE'].includes(method))data.mutations.push({path,method,status:response.status()});
 });
 page.on('requestfinished',request=>{
  const path=new URL(request.url()).pathname;
  if(request.method()==='GET'&&/^\/api\/files\/[^/]+$/.test(path)){
   const timing=request.timing();
   void request.response().then(response=>{if(response)data.detailReads.push({path,status:response.status(),elapsedMs:timing.responseEnd});});
  }
 });
 page.on('requestfailed',request=>{
  const path=new URL(request.url()).pathname;
  if(path.startsWith('/api/'))data.requestFailures.push({path,error:request.failure()?.errorText||'Unknown transport failure'});
 });
});
test.afterEach(async({page},info)=>{
 await info.attach('browser-diagnostics',{body:JSON.stringify(diagnostics.get(page),null,2),contentType:'application/json'});
});
test('register, upload, inspect, and navigate real workspace',async({page},testInfo)=>{
 test.setTimeout(300000);
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 const email=`browser-${Date.now()}-${Math.random().toString(16).slice(2)}@example.test`;
 const password='browser-test-password';
 const first=Buffer.from('Harmless browser fixture');
 async function navigate(label:string){
  const toggle=page.getByRole('button',{name:'Toggle navigation'});
  const mobile=await toggle.isVisible();
  if(mobile)await toggle.click();
  await page.getByRole('link',{name:label,exact:true}).click();
  if(mobile)await expect.poll(()=>page.locator('aside').evaluate(element=>element.getBoundingClientRect().right)).toBeLessThanOrEqual(1);
 }
 async function verifyDownload(content:Buffer){
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download current version'}).click()]);
  const destination=await download.path();expect(destination).not.toBeNull();
  expect(await readFile(destination!)).toEqual(content);
 }
 await registerWorkspace(page,email,password);
 await page.getByRole('button',{name:'Upload files'}).click();
 await page.locator('input[type=file]').first().setInputFiles({name:'browser-proof.txt',mimeType:'text/plain',buffer:first});
 await expect(page.getByRole('button',{name:/browser-proof.txt/}).first()).toBeVisible();
 // Worker/model activity can delay the locked detail read. Await the real
 // response with a bounded budget, fail on non-200, then assert rendered data.
 const detailResponse=page.waitForResponse(response=>response.request().method()==='GET'&&/^\/api\/files\/[^/]+$/.test(new URL(response.url()).pathname),{timeout:30000});
 await page.getByRole('button',{name:/browser-proof.txt/}).first().click();
 const loadedDetail=await detailResponse;
 expect(loadedDetail.status(),'File details must load successfully from the API').toBe(200);
 expect(await loadedDetail.json()).toMatchObject({file:{name:'browser-proof.txt'},versions:[{digest:createHash('sha256').update(first).digest('hex')}]});
 await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByRole('dialog').getByText('SHA-256',{exact:true})).toBeVisible();
 const dialog=page.getByRole('dialog');
 await expect(dialog.getByText(createHash('sha256').update(first).digest('hex'),{exact:true})).toBeVisible();
 await dialog.getByRole('button',{name:'Storage',exact:true}).click();
 await expect(dialog.getByRole('region',{name:'File storage location'})).toBeVisible();
 await expect(dialog.getByText((await loadedDetail.json()).versions[0].storage_key,{exact:true})).toBeVisible();
 await dialog.getByRole('button',{name:'Evidence',exact:true}).click();
 await expect(dialog.locator('.detail-summary .badge')).toHaveText(/^approved$/i,{timeout:180000});
 await verifyDownload(first);
 await dialog.getByRole('button',{name:'Open reader',exact:true}).click();
 await expect(dialog.locator('.preview pre')).toHaveText(first.toString());
 await dialog.getByRole('button',{name:'Close preview'}).click();
 await dialog.getByLabel('New file name').fill('browser-renamed.txt');
 const renameResponse=page.waitForResponse(response=>response.request().method()==='PATCH'&&/^\/api\/files\/[^/]+$/.test(new URL(response.url()).pathname));
 await dialog.getByRole('button',{name:'Rename',exact:true}).click();
 const renamed=await renameResponse;
 expect(renamed.status(),'Rename must be confirmed by the API').toBe(200);
 expect(renamed.request().postDataJSON()).toEqual({name:'browser-renamed.txt'});
 expect(await renamed.json()).toMatchObject({ok:true});
 await expect(dialog.getByRole('heading',{name:'browser-renamed.txt',exact:true})).toBeVisible({timeout:15000});
 await expect(dialog.getByRole('button',{name:'Rename',exact:true})).toBeEnabled();
 const second=Buffer.from('Harmless browser fixture version two, with different bytes.');
 await dialog.locator('input[type=file]').setInputFiles({name:'browser-renamed.txt',mimeType:'text/plain',buffer:second});
 await expect(dialog.locator('.detail-summary p')).toContainText('v2');
 await expect(dialog.getByText(createHash('sha256').update(second).digest('hex'),{exact:true})).toBeVisible();
 await expect(dialog.locator('.detail-summary .badge')).toHaveText(/^approved$/i,{timeout:180000});
 await verifyDownload(second);
 await dialog.getByRole('button',{name:'Versions',exact:true}).click();
 await expect(dialog.locator('.version-list>div')).toHaveCount(2);
 await expect(dialog.locator('.version-list button:disabled')).toHaveCount(1);
 await dialog.getByRole('button',{name:'Activity',exact:true}).click();
 await expect(dialog.locator('.event-list')).toBeVisible();
 await page.screenshot({path:testInfo.outputPath('file-history.png'),fullPage:true});
 await page.getByRole('button',{name:'Close dialog'}).click();
 await navigate('Verification queue');await expect(page.getByRole('heading',{name:'Verification queue'})).toBeVisible();
 await expect(page.getByLabel('Scheduling algorithm')).toBeVisible();
 for(const method of ['fifo','edf','rule']){
  await page.getByLabel('Scheduling algorithm').selectOption(method);
  await expect.poll(async()=>{const response=await page.request.get('/api/scheduler');expect(response.ok()).toBeTruthy();return (await response.json()).strategy}).toBe(method);
 }
 await page.getByRole('button',{name:'Scheduling decisions',exact:true}).click();
 await expect(page.locator('.decision-list')).toBeVisible();
 await page.screenshot({path:testInfo.outputPath('verification-queue.png'),fullPage:true});
 await navigate('Research lab');
 await expect(page.getByRole('heading',{name:'Workload prediction models'})).toBeVisible();
 await expect(page.getByRole('status')).toHaveCount(0);
 await expect(page.getByRole('alert')).toHaveCount(0);
 await page.screenshot({path:testInfo.outputPath('research-lab.png'),fullPage:true});
 for(const [label,heading] of [['Overview','Workspace overview'],['All files','All files'],['Sharing','Sharing'],['Security operations','Security operations'],['Temporal graph','Temporal graph'],['Security assistant','Security assistant']]){
  await navigate(label);
  await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible();
  await expect(page.getByRole('status')).toHaveCount(0);
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.screenshot({path:testInfo.outputPath(label.toLowerCase().replaceAll(' ','-')+'.png'),fullPage:true});
 }
 const toggle=page.getByRole('button',{name:'Toggle navigation'});
 if(await toggle.isVisible())await toggle.click();
 const logoutResponse=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/auth/logout'&&response.request().method()==='POST');
 await page.getByRole('button',{name:'Sign out'}).click();
 expect((await logoutResponse).status(),'Server must confirm logout before the view changes').toBe(200);
 await page.waitForURL(url=>url.pathname==='/');
 await expect(page.getByRole('heading',{name:'Welcome back'})).toBeVisible({timeout:15000});
 expect((await page.request.get('/api/auth/me')).status(),'Signed-out browser must be denied protected APIs').toBe(401);
 await page.getByLabel('Email address').fill(email);
 await page.getByLabel('Password',{exact:true}).fill('incorrect-browser-password');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('alert')).toBeVisible();
 await page.getByLabel('Password',{exact:true}).fill(password);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Workspace overview'})).toBeVisible();
 await page.reload();
 await expect(page.getByRole('heading',{name:'Workspace overview'})).toBeVisible();
 // Revoke this fixture's session outside the UI, as with expiry or another tab.
 // The next protected read must leave the mounted private workspace without a
 // manual refresh. This uses real endpoints, not a clock/database mutation.
 const currentSession=await page.request.get('/api/auth/me');
 expect(currentSession.status()).toBe(200);
 const sessionData=await currentSession.json();
 const revoked=await page.request.post('/api/auth/logout',{headers:{Origin:new URL(page.url()).origin,'X-CSRF-Token':sessionData.csrf}});
 expect(revoked.status()).toBe(200);
 const expiryToggle=page.getByRole('button',{name:'Toggle navigation'});
 if(await expiryToggle.isVisible())await expiryToggle.click();
 await page.getByRole('link',{name:'All files',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Welcome back'})).toBeVisible({timeout:15000});
 await expect(page).toHaveURL(/\/$/);
 expect((await page.request.get('/api/auth/me')).status()).toBe(401);
 await page.screenshot({path:testInfo.outputPath('session-expired.png'),fullPage:true});
 expect(errors).toEqual([]);
 expect(diagnostics.get(page)?.cspViolations).toEqual([]);
});
