import {defineConfig} from '@playwright/test';

// No page/browser fixtures: these tests execute in Node without Chromium.
export default defineConfig({
  testDir: './unit',
  workers: 1,
  outputDir: 'test-results/unit',
  reporter: [['list'], ['json', {outputFile: 'test-results/unit-report.json'}]],
});
