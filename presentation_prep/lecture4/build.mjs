import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {layout,e} from './layouts.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url));
const slides=JSON.parse(await fs.readFile(path.join(dir,'slides.json'),'utf8'));
let content='';
for(const [i,s] of slides.entries()){
 const n=i+1;const lid=s.layout_id;const special=s.kind==='cover'||s.kind==='divider';const cls=s.kind==='cover'?'cover':special?'divider':'content-slide';
 const notes=[s.notes||'',...(s.sources||[]).map(u=>`<a href="${e(u)}">${e(u)}</a>`)];
 content+=`<section class="slide ${cls}" data-slide="${n}" data-layout="${lid}" id="slide-${n}" aria-label="${e(s.title)}">${special?'<div class="slide-frame"></div>':`<p class="section-tag">${e(s.section||'LECTURE 4')}</p><h2>${e(s.title)}</h2>`}<div class="content">${layout(lid,s)}</div><aside class="notes">${notes.map((t,j)=>`<p>${j? t:e(t)}</p>`).join('')}</aside></section>\n`;
}
const controls=`<div class="deck-controls"><button id="previous">← Previous</button><span id="slide-counter"></span><button id="next">Next →</button><button id="present" aria-pressed="false">Present</button><button id="notes">Notes</button></div><aside id="notes-dialog" class="notes-dialog" hidden><button id="close-notes">Close</button><div id="notes-content"></div></aside>`;
await fs.writeFile(path.join(dir,'lecture4.html'),`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Lecture 4: MLflow tracing, evaluation and observability</title><link rel="stylesheet" href="lecture4.css"></head><body><main>${content}</main>${controls}<script src="lecture4.js"></script></body></html>`);
console.log(`Built ${slides.length} slides with native HTML and SVG`);
