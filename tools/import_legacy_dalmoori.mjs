// Legacy FFR cells contain onset or vowel/coda pieces, in addition to syllables.
// Select the native Dalmoori variant using the unmodified upstream composer,
// then omit the onset layer for a cell that stores only a vowel/coda piece.
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
const [checkout,input,output]=process.argv.slice(2);
const base=resolve(checkout,'generator');
const {Syllable}=await import(pathToFileURL(join(base,'dist/core/hangul-syllable.js')));
const {combine}=await import(pathToFileURL(join(base,'dist/core/combine.js')));
const requests=JSON.parse(await readFile(input,'utf8'));
const results=[];
for(const request of requests){
  const syllable=await Syllable.of(join(base,'glyph'),'ㅇ',request.vowel,request.coda||undefined);
  const originalOnset=syllable.onset;
  const onset=Object.create(originalOnset);
  onset.find=(...args)=>originalOnset.find(...args).map(part=>({
    ...part,
    font:{with(nucleus){
      const original=part.font.with(nucleus);
      return {with(coda){
        original.with(coda); // Preserve the upstream collision/variant decision.
        return nucleus.with(coda);
      }};
    }},
  }));
  const font=combine(onset,syllable.nucleus,syllable.coda);
  results.push({...request,bitmap:font.renderAsciiFont(),width:font.width,height:font.height});
}
await writeFile(output,JSON.stringify(results,null,2)+'\n','utf8');
