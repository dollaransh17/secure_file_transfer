import {test, expect} from '@playwright/test';
import {QueryClient} from '@tanstack/react-query';
import {renameFile} from '../src/file-actions';
import {setCsrf} from '../src/api';

const originalFetch = globalThis.fetch;
let client: QueryClient;
test.beforeEach(() => {
  client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  setCsrf('unit-test-csrf');
  client.setQueryData(['detail-file'], {file: {id: 'file', name: 'old.txt'}, versions: [{id: 'v1', status: 'PENDING'}]});
  client.setQueryData(['files'], [{id: 'file', name: 'old.txt'}, {id: 'other', name: 'other.txt'}]);
});
test.afterEach(() => {client.clear(); globalThis.fetch = originalFetch; setCsrf('');});

test('rename waits for server confirmation, then updates metadata in both caches', async () => {
  let finish!: (response: Response) => void;
  globalThis.fetch = async (url, options) => {
    expect(url).toBe('/api/files/file');
    expect(options?.method).toBe('PATCH');
    expect(JSON.parse(options?.body as string)).toEqual({name: 'new.txt'});
    expect(new Headers(options?.headers).get('X-CSRF-Token')).toBe('unit-test-csrf');
    return new Promise<Response>(resolve => {finish = resolve;});
  };
  const action = renameFile(client, 'file', 'new.txt');
  expect(client.getQueryData<any>(['detail-file']).file.name).toBe('old.txt');
  finish(Response.json({ok: true}));
  await action;
  expect(client.getQueryData<any>(['detail-file'])).toEqual({file: {id: 'file', name: 'new.txt'}, versions: [{id: 'v1', status: 'PENDING'}]});
  expect(client.getQueryData(['files'])).toEqual([{id: 'file', name: 'new.txt'}, {id: 'other', name: 'other.txt'}]);
});

for (const status of [403, 422, 429, 500]) {
  test(`HTTP ${status} cannot rename cached data`, async () => {
    globalThis.fetch = async () => Response.json({detail: 'Rename rejected'}, {status});
    await expect(renameFile(client, 'file', 'new.txt')).rejects.toMatchObject({status});
    expect(client.getQueryData<any>(['detail-file']).file.name).toBe('old.txt');
    expect(client.getQueryData<any[]>(['files'])?.[0].name).toBe('old.txt');
  });
}

test('unconfirmed responses cannot rename cached data', async () => {
  globalThis.fetch = async () => Response.json({ok: false});
  await expect(renameFile(client, 'file', 'new.txt')).rejects.toThrow('did not confirm');
  expect(client.getQueryData<any>(['detail-file']).file.name).toBe('old.txt');
});

test('a stale in-flight detail read cannot overwrite a confirmed rename', async () => {
  let finishRead!: (value: unknown) => void;
  const pending = client.fetchQuery({queryKey: ['detail-file'], queryFn: () => new Promise(resolve => {finishRead = resolve;})}).catch(() => undefined);
  globalThis.fetch = async () => Response.json({ok: true});
  await renameFile(client, 'file', 'new.txt');
  finishRead({file: {id: 'file', name: 'old.txt'}});
  await pending;
  expect(client.getQueryData<any>(['detail-file']).file.name).toBe('new.txt');
});

test('a rename does not invent an uncached detail record', async () => {
  client.removeQueries({queryKey: ['detail-file']});
  globalThis.fetch = async () => Response.json({ok: true});
  await renameFile(client, 'file', 'new.txt');
  expect(client.getQueryData(['detail-file'])).toBeUndefined();
});
