import {test, expect} from '@playwright/test';
import {dependencyIssues, policy} from '../scripts/check-dependencies.mjs';

function fixture() {
  return {manifest: {dependencies: {...policy}}, lock: {packages: {
    '': {dependencies: {...policy}},
    ...Object.fromEntries(Object.entries(policy).map(([name, version]) => ['node_modules/' + name, {version}])),
  }}, installed: {...policy}};
}

test('manifest, lock and installed versions must agree on the patched targets', () => {
  const {manifest, lock, installed} = fixture();
  expect(dependencyIssues(manifest, lock, installed)).toEqual([]);
});

test('a patched manifest cannot conceal a vulnerable lockfile', () => {
  const {manifest, lock, installed} = fixture();
  lock.packages['node_modules/zod'].version = '3.25.76';
  expect(dependencyIssues(manifest, lock, installed).join(' ')).toContain('regenerate the lockfile');
});

test('a patched lockfile cannot conceal old installed packages', () => {
  const {manifest, lock, installed} = fixture();
  installed.zod = '3.25.76';
  expect(dependencyIssues(manifest, lock, installed).join(' ')).toContain('installed 3.25.76');
});

test('the legacy resolver cannot remain installed during the Zod upgrade', () => {
  const {manifest, lock, installed} = fixture();
  installed['@hookform/resolvers'] = '3.10.0';
  expect(dependencyIssues(manifest, lock, installed).join(' ')).toContain('@hookform/resolvers');
});
