export const $=id=>document.getElementById(id);
export function el(tag,text='',className=''){const n=document.createElement(tag);n.textContent=text;if(className)n.className=className;return n;}
export function link(text,url){const a=el('a',text);try{const u=new URL(url);if(u.protocol==='https:'){a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';}}catch{}return a;}
export function download(name,content,type='application/json'){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export function csv(rows){return rows.map(row=>row.map(v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replaceAll('"','""')+'"').join(',')).join('\r\n');}
export function share(params){const url=new URL(location.href);url.hash=new URLSearchParams(params).toString();history.replaceState(null,'',url);$('share-url').value=url.href;$('share-box').hidden=false;}
export function baseMap(id,center,zoom){const map=L.map(id,{preferCanvas:true,scrollWheelZoom:false}).setView(center,zoom);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).on('tileerror',()=>{const n=$('map-notice');if(n){n.hidden=false;n.textContent='Some background tiles could not load. Records and overlays remain available.';}}).addTo(map);L.control.scale({imperial:false}).addTo(map);return map;}
export function fillSelect(id,values){for(const v of [...new Set(values)].filter(Boolean).sort())$(id).append(new Option(v,v));}
export function dateLabel(iso){return iso?new Date(iso).toLocaleDateString('en-CA',{timeZone:'UTC',year:'numeric',month:'short',day:'numeric'}):'Not supplied';}
