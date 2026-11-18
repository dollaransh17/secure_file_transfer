import {expect,type Page} from '@playwright/test';

export async function openPage(page:Page,path:string){
 const response=await page.goto(path,{waitUntil:'domcontentloaded',timeout:30000});
 expect(response?.status(),`Frontend document ${path} must load successfully`).toBe(200);
}

export async function registerWorkspace(page:Page,email:string,password:string){
 await openPage(page,'/');
 await expect(page.getByRole('heading',{name:'Welcome back',exact:true})).toBeVisible({timeout:30000});
 await page.getByRole('button',{name:'New to Prooflane? Create a workspace'}).click();
 await page.getByLabel('Email address').fill(email);
 await page.getByLabel('Password',{exact:true}).fill(password);
 const registered=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/auth/register',{timeout:30000});
 await page.getByRole('button',{name:'Create workspace',exact:true}).click();
 expect((await registered).status(),'Workspace registration must succeed before navigation').toBe(200);
 await expect(page.getByRole('heading',{name:'Workspace overview',exact:true})).toBeVisible({timeout:15000});
}
