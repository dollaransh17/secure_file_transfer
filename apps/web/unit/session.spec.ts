import {test, expect} from '@playwright/test';
import {csrf, setCsrf, ApiError} from '../src/api';
import {endSession} from '../src/session';

const originalFetch = globalThis.fetch;
test.beforeEach(() => setCsrf('unit-test-csrf'));
test.afterEach(() => {globalThis.fetch = originalFetch; setCsrf('');});

test('logout waits for server confirmation and sends the active CSRF token', async () => {
  let finish!: (response: Response) => void;
  let redirected = false;
  globalThis.fetch = async (url, options) => {
    expect(url).toBe('/api/auth/logout');
    expect(options?.method).toBe('POST');
    expect(options?.credentials).toBe('include');
    expect(new Headers(options?.headers).get('X-CSRF-Token')).toBe('unit-test-csrf');
    return new Promise<Response>(resolve => {finish = resolve;});
  };
  const action = endSession(() => {expect(csrf).toBe(''); redirected = true;});
  expect(redirected).toBe(false);
  expect(csrf).toBe('unit-test-csrf');
  finish(Response.json({ok: true}));
  await action;
  expect(redirected).toBe(true);
});

test('an already-expired session returns to the signed-out page', async () => {
  let redirects = 0;
  globalThis.fetch = async () => Response.json({detail: 'Session expired'}, {status: 401});
  await endSession(() => redirects++);
  expect(redirects).toBe(1);
  expect(csrf).toBe('');
});

for (const [status, message] of [[403, 'CSRF validation failed'], [429, 'Rate limit exceeded'], [500, 'Server error']] as const) {
  test(`HTTP ${status} cannot be presented as successful logout`, async () => {
    let redirects = 0;
    globalThis.fetch = async () => Response.json({detail: message}, {status});
    await expect(endSession(() => redirects++)).rejects.toMatchObject({status, message});
    expect(redirects).toBe(0);
    expect(csrf).toBe('unit-test-csrf');
  });
}

test('a network failure retains the session view for retry', async () => {
  let redirects = 0;
  globalThis.fetch = async () => {throw new TypeError('Network interrupted');};
  await expect(endSession(() => redirects++)).rejects.toThrow('Network interrupted');
  expect(redirects).toBe(0);
  expect(csrf).toBe('unit-test-csrf');
});

test('plaintext rate-limit responses remain errors', async () => {
  let redirects = 0;
  globalThis.fetch = async () => new Response('Rate limit exceeded', {status: 429, statusText: 'Too Many Requests'});
  const result = endSession(() => redirects++);
  await expect(result).rejects.toBeInstanceOf(ApiError);
  expect(redirects).toBe(0);
  expect(csrf).toBe('unit-test-csrf');
});
