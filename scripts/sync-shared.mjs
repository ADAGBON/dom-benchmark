// Copies the shared harness + stylesheet into every app so all four use identical files.
import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const targets = {
  'react-todo': 'src/shared',
  'vue-todo': 'src/shared',
  'svelte-todo': 'src/shared',
  'angular-todo': 'src/shared',
};

for (const [app, dir] of Object.entries(targets)) {
  const dest = join(root, app, dir);
  mkdirSync(dest, { recursive: true });
  const files = ['bench-harness.js', 'todo.css'];
  if (app === 'angular-todo') files.push('bench-harness.d.ts'); // types for the TS app
  for (const f of files) copyFileSync(join(root, 'shared', f), join(dest, f));
  console.log(`synced shared files -> ${app}/${dir}`);
}
