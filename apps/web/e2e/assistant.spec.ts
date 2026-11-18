import {test,expect} from '@playwright/test';
import {openPage,registerWorkspace} from './support';

// Browser-rendering regression only. Registration/session APIs remain real;
// assistant transport is explicitly mocked to avoid provider charges. These
// fixtures do not establish citation authorization or real Claude behavior.
for(const scrollResult of ['void','promise'] as const){
 test(`chat stays mounted with ${scrollResult}-returning scrollIntoView (mock assistant transport)`,async({page})=>{
  test.setTimeout(90000);
  const errors:string[]=[];
  const submitted:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(({promise})=>{
   const original=Element.prototype.scrollIntoView;
   Element.prototype.scrollIntoView=function(...args:Parameters<typeof original>){
    original.apply(this,args);
    // Exercise both browser contracts, including Promise-returning scrolling.
    return promise?Promise.resolve({interrupted:false}):undefined;
   };
  },{promise:scrollResult==='promise'});
  const eventId='00000000-0000-4000-8000-000000000001';
  await page.route('**/api/assistant',async route=>{
   if(route.request().method()!=='POST'){await route.continue();return;}
   submitted.push(route.request().postDataJSON().question);
   await route.fulfill({json:{
    answer:`Browser regression fixture: verification event recorded [${eventId}].`,
    events:[{id:eventId,kind:'VERIFICATION_APPROVED',timestamp:1794820000}],
    status:'evidence_only',usage:{},
   }});
  });
  await registerWorkspace(page,`chat-ui-${Date.now()}-${Math.random().toString(16).slice(2)}@example.test`,'browser-test-password');
  await openPage(page,'/assistant');
  await expect(page.getByRole('heading',{name:'Security assistant',exact:true})).toBeVisible();
  const questions=['Explain the browser fixture event.','Which event supports that explanation?'];
  for(const [index,question] of questions.entries()){
   await page.getByLabel('Ask about security events').fill(question);
   await page.getByRole('button',{name:'Send question'}).click();
   await expect(page.getByText('Prooflane assistant',{exact:true})).toHaveCount(index+1);
   await expect(page.getByLabel('Send question')).toBeDisabled();
   await expect(page.locator('.chat-message.assistant')).toHaveCount(index+1);
   await expect(page.getByRole('heading',{name:'Security assistant',exact:true})).toBeVisible();
  }
  expect(submitted).toEqual(['Explain the browser fixture event.','Which event supports that explanation?']);
  await expect(page.locator('.chat-message.user')).toHaveCount(2);
  await expect(page.locator('.chat-message.assistant')).toHaveCount(2);
  await page.getByText('1 authorized event references',{exact:true}).first().click();
  await expect(page.locator('.citation code').first()).toHaveText(`[${eventId}]`);
  // A client-side route change also runs effect cleanup.
  const toggle=page.getByRole('button',{name:'Toggle navigation'});
  if(await toggle.isVisible())await toggle.click();
  await page.getByRole('link',{name:'All files',exact:true}).click();
  await expect(page.getByRole('heading',{name:'All files',exact:true})).toBeVisible();
  expect(errors).toEqual([]);
 });
}
