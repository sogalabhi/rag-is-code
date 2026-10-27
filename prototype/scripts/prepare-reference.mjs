import { copyFile, mkdir } from 'node:fs/promises';

const destination = new URL('../public/reference/', import.meta.url);
await mkdir(destination, { recursive: true });
await copyFile(new URL('../../data/is.800.2007.pdf', import.meta.url), new URL('codebook.pdf', destination));
for (const name of ['table-05.png', 'table-19.png', 'figure-05.png']) {
  await copyFile(new URL(`../../data/review_assets/${name}`, import.meta.url), new URL(name, destination));
}
console.log('Prepared the original PDF and three source crops for local preview.');
