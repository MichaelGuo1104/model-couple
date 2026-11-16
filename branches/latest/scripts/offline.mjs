import { readFileSync, writeFileSync } from 'node:fs';
// Rollup emits one IIFE. Classic defer script also works under file://.
const path = new URL('../dist/index.html', import.meta.url);
let html = readFileSync(path, 'utf8');
html = html.replace(/<script\b[^>]*src="([^"]+)"[^>]*><\/script>/g, '<script defer src="$1"></script>');
html = html.replace(/\s+crossorigin(?:="[^"]*")?/g, '');
if (/type="module"|modulepreload/.test(html)) throw new Error('Offline build still contains module references');
writeFileSync(path, html);
console.log('Offline entry ready: dist/index.html (no server required).');
