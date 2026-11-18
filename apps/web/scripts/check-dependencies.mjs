import {readFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
export const policy = JSON.parse(readFileSync(join(root, 'security-dependencies.json'), 'utf8'));

export function dependencyIssues(manifest, lock, installed) {
  const issues = [];
  for (const [name, version] of Object.entries(policy)) {
    if (manifest.dependencies?.[name] !== version) issues.push(`${name}: manifest must pin ${version}`);
    if (lock.packages?.['']?.dependencies?.[name] !== version || lock.packages?.['node_modules/' + name]?.version !== version) {
      issues.push(`${name}: regenerate the lockfile for ${version}`);
    }
    if (installed && installed[name] !== version) issues.push(`${name}: installed ${installed[name] || 'missing'}, expected ${version}`);
  }
  return issues;
}

function main() {
  const manifest = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  const lock = JSON.parse(readFileSync(join(root, 'package-lock.json'), 'utf8'));
  let installed;
  if (!process.argv.includes('--lock-only')) {
    installed = {};
    for (const name of Object.keys(policy)) {
      try {installed[name] = JSON.parse(readFileSync(join(root, 'node_modules', name, 'package.json'), 'utf8')).version;}
      catch {installed[name] = null;}
    }
  }
  const issues = dependencyIssues(manifest, lock, installed);
  if (issues.length) {
    console.error(issues.join('\n') + '\nRun ./scripts/fix-web-audit.sh from the repository root.');
    process.exitCode = 1;
  } else console.log('Security dependency versions match manifest, lockfile' + (installed ? ' and installed packages.' : '.'));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
