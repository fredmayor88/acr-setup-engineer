// Decompresses Oodle-compressed IoStore blocks. Reads a job list produced by
// extract_torque_curves.py and writes each reconstructed chunk to its `out` path.
//
// Why node: ACR (UE 5.x) uses Oodle 2.9-era compression. The oo2core DLLs that ship
// with older games reject these blocks, and Epic doesn't redistribute a standalone
// decoder, so we use the ooz-wasm reimplementation. `npm install` in this folder.

import { decompress } from 'ooz-wasm';
import fs from 'fs';

const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

for (const job of jobs) {
  const fd = fs.openSync(job.cas, 'r');
  const parts = [];
  for (const [off, csize, usize, method] of job.blocks) {
    const buf = Buffer.alloc(csize);
    fs.readSync(fd, buf, 0, csize, off);
    // method 0 is stored uncompressed; anything else is Oodle
    parts.push(method === 0 ? buf.subarray(0, usize) : Buffer.from(decompress(buf, usize)));
  }
  fs.closeSync(fd);
  const all = Buffer.concat(parts);
  fs.writeFileSync(job.out, all.subarray(job.start, job.start + job.len));
}

console.log(`unpacked ${jobs.length} chunk(s)`);
