import {test, expect} from '@playwright/test';
import {zodResolver} from '@hookform/resolvers/zod';
import {authSchema, type AuthValues} from '../src/auth-schema';

const options = {criteriaMode: 'all' as const, fields: {}, shouldUseNativeValidation: false};
const resolve = zodResolver(authSchema);
const valid = {email: 'validation@example.invalid', password: 'valid-fixture-password'};

test('valid credentials pass the actual form resolver', async () => {
  const result = await resolve(valid, {}, options);
  expect(result.errors).toEqual({});
  expect(result.values).toEqual(valid);
});

test('invalid email maps to a field error rather than throwing', async () => {
  const result = await resolve({...valid, email: 'invalid'}, {}, options);
  expect(result.errors.email?.message).toBeTruthy();
  expect(result.values).toEqual({});
});

test('short passwords preserve the user-facing validation message', async () => {
  const result = await resolve({...valid, password: 'short'}, {}, options);
  expect(result.errors.password?.message).toBe('Use at least 12 characters');
});

test('password limits match the backend at 12 and 128 characters', () => {
  for (const length of [12, 128]) expect(authSchema.safeParse({...valid, password: 'a'.repeat(length)}).success).toBe(true);
  for (const length of [11, 129]) expect(authSchema.safeParse({...valid, password: 'a'.repeat(length)}).success).toBe(false);
});

test('oversized email and password input produce bounded field errors', async () => {
  const result = await resolve({email: 'a'.repeat(255) + '@example.invalid', password: 'a'.repeat(129)}, {}, options);
  expect(result.errors.email).toBeTruthy();
  expect(result.errors.password?.message).toBe('Use at most 128 characters');
});

test('collection-shaped credential input is rejected without an exception', async () => {
  const input = {email: ['unexpected'], password: {nested: 'unexpected'}} as unknown as AuthValues;
  const result = await resolve(input, {}, options);
  expect(result.errors.email).toBeTruthy();
  expect(result.errors.password).toBeTruthy();
  expect(result.values).toEqual({});
});

test('unregistered fields are not returned in credential payloads', async () => {
  const result = await resolve({...valid, extra: 'discard'} as AuthValues, {}, options);
  expect(result.values).toEqual(valid);
});
