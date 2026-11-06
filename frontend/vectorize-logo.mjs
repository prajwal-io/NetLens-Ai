import fs from 'node:fs';
import {PNG} from 'pngjs';
import ImageTracer from 'imagetracerjs';
const png=PNG.sync.read(fs.readFileSync('public/logo-transparent.png'));
const pal=[{r:0,g:0,b:0,a:0},{r:0,g:83,b:255,a:255},{r:100,g:175,b:239,a:255},{r:23,g:28,b:42,a:255},{r:255,g:255,b:255,a:255},{r:239,g:73,b:65,a:255},{r:66,g:199,b:96,a:255}];
const svg=ImageTracer.imagedataToSVG({width:png.width,height:png.height,data:png.data},{ltres:2,qtres:2,pathomit:32,blurradius:2,blurdelta:50,linefilter:true,pal,colorsampling:0,colorquantcycles:1,strokewidth:0,roundcoords:1,viewbox:true,desc:false});
fs.writeFileSync('public/logo.svg',svg);
console.log('Vector logo:',svg.length,'bytes; native paths, no embedded bitmap.');
