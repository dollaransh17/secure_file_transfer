import {test, expect} from '@playwright/test';
import {api, csrf, setCsrf, onSessionExpired, handleUnauthorized} from '../src/api';

const originalFetch=globalThis.fetch;
let remove:(()=>void)|undefined;
test.beforeEach(()=>setCsrf('active-session'));
test.afterEach(()=>{remove?.();remove=undefined;globalThis.fetch=originalFetch;setCsrf('');});

test('a protected request denied with 401 triggers signed-out navigation',async()=>{
 let count=0;remove=onSessionExpired(()=>count++);
 globalThis.fetch=async()=>Response.json({detail:'Session expired'},{status:401});
 await expect(api('/scheduler')).rejects.toMatchObject({status:401});
 expect(count).toBe(1);expect(csrf).toBe('');
});

test('initial unauthenticated session lookup does not create a reload loop',async()=>{
 let count=0;remove=onSessionExpired(()=>count++);setCsrf('');
 globalThis.fetch=async()=>Response.json({detail:'Session expired'},{status:401});
 await expect(api('/auth/me')).rejects.toMatchObject({status:401});
 expect(count).toBe(0);
});

test('a wrong-password login retains its error instead of redirecting',async()=>{
 let count=0;remove=onSessionExpired(()=>count++);
 globalThis.fetch=async()=>Response.json({detail:'Invalid email or password'},{status:401});
 await expect(api('/auth/login',{method:'POST'})).rejects.toThrow('Invalid email or password');
 expect(count).toBe(0);expect(csrf).toBe('active-session');
});

test('an old request cannot sign out a newer login',async()=>{
 let finish!:(response:Response)=>void;let count=0;remove=onSessionExpired(()=>count++);
 globalThis.fetch=async()=>new Promise<Response>(resolve=>{finish=resolve;});
 const pending=api('/files').catch(error=>error);
 setCsrf('new-session');finish(Response.json({detail:'Session expired'},{status:401}));
 expect((await pending).status).toBe(401);
 expect(count).toBe(0);expect(csrf).toBe('new-session');
});

test('concurrent denied requests trigger only one navigation',async()=>{
 let count=0;remove=onSessionExpired(()=>count++);
 globalThis.fetch=async()=>Response.json({detail:'Session expired'},{status:401});
 await Promise.all([api('/files').catch(()=>{}),api('/events').catch(()=>{})]);
 expect(count).toBe(1);
});

for(const status of [403,429,500]){
 test(`HTTP ${status} does not claim the session expired`,async()=>{
  let count=0;remove=onSessionExpired(()=>count++);
  globalThis.fetch=async()=>Response.json({detail:'Request rejected'},{status});
  await expect(api('/files')).rejects.toMatchObject({status});
  expect(count).toBe(0);expect(csrf).toBe('active-session');
 });
}

test('upload unauthorized handling follows the same session identity guard',()=>{
 let count=0;remove=onSessionExpired(()=>count++);
 handleUnauthorized('/files','old-session');expect(count).toBe(0);
 handleUnauthorized('/files','active-session');expect(count).toBe(1);expect(csrf).toBe('');
});

test('cleanup of an older subscriber does not remove its replacement',()=>{
 let count=0;const old=onSessionExpired(()=>{throw new Error('Old subscriber');});
 remove=onSessionExpired(()=>count++);old();
 handleUnauthorized('/files','active-session');expect(count).toBe(1);
});
