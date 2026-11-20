// SPDX-License-Identifier: MIT
// Single-page web UI served at "/". Plain HTML + JS, no external files (works without internet).
#pragma once
#include <pgmspace.h>

const char INDEX_HTML[] PROGMEM = R"HTML(<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 IR Blaster</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--fg:#1d232b;--mut:#677281;--acc:#2563eb;--bad:#c2410c;--bd:#dfe3e8}
@media(prefers-color-scheme:dark){:root{--bg:#12161c;--card:#1b2129;--fg:#e6e9ee;--mut:#9aa4b2;--acc:#60a5fa;--bad:#fb923c;--bd:#2b333d}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
main{max-width:760px;margin:0 auto;padding:16px}h1{font-size:20px;margin:4px 0 2px}small,.mut{color:var(--mut)}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px;margin:12px 0}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input{flex:1;min-width:140px;padding:9px 10px;border:1px solid var(--bd);border-radius:8px;background:var(--bg);color:var(--fg);font:inherit}
button{padding:9px 14px;border:0;border-radius:8px;background:var(--acc);color:#fff;font:inherit;cursor:pointer}
button.ghost{background:transparent;color:var(--fg);border:1px solid var(--bd)}button.bad{background:var(--bad)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.code{border:1px solid var(--bd);border-radius:8px;padding:8px}.code b{display:block;word-break:break-all}
.code .row{margin-top:6px}.code button{padding:6px 10px;font-size:13px}
pre{white-space:pre-wrap;word-break:break-all;font-size:12px;margin:6px 0 0}
#msg{min-height:1.4em}
</style></head><body><main>
<h1>ESP32 IR Blaster</h1><small id="st">connecting...</small>
<div class="card"><b>Learn a code</b>
 <div class="row" style="margin-top:8px"><input id="nm" maxlength="32" placeholder="name, e.g. tv_power">
 <button onclick="learnIt()">Learn</button></div>
 <div id="msg" class="mut"></div></div>
<div class="card"><div class="row" style="justify-content:space-between"><b>Saved codes</b>
 <span class="row"><button class="ghost" onclick="location='/api/export'">Export</button>
 <label class="ghost" style="padding:8px 12px;border:1px solid var(--bd);border-radius:8px;cursor:pointer">Import
 <input type="file" accept=".json" style="display:none" onchange="imp(this)"></label></span></div>
 <div id="codes" class="grid" style="margin-top:10px"></div></div>
<div class="card"><b>Last received</b><pre id="last" class="mut">nothing yet - point a remote at the board</pre></div>
<div class="card row" style="justify-content:space-between"><small>USER button: tap = send "button", hold 1 s = learn "button", hold 5 s = reset Wi-Fi</small>
 <button class="ghost" onclick="if(confirm('Forget Wi-Fi and reboot into setup mode?'))post('/api/wifi-reset')">Reset Wi-Fi</button></div>
</main><script>
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function post(u,body){const r=await fetch(u,{method:'POST',body});return r.json().catch(()=>({}))}
async function load(){const c=await (await fetch('/api/codes')).json();
 $('codes').innerHTML=c.length?c.map(x=>`<div class="code"><b>${esc(x.name)}</b><small>${esc(x.protocol)}${x.bits?' / '+x.bits+' bit':''}</small>
 <div class="row"><button onclick="send('${encodeURIComponent(x.name)}')">Send</button>
 <button class="ghost" onclick="ren('${encodeURIComponent(x.name)}')">Rename</button>
 <button class="ghost" onclick="del('${encodeURIComponent(x.name)}')">&#x2715;</button></div></div>`).join(''):'<small>No codes yet. Learn one above.</small>'}
async function send(n){const r=await post('/api/send?name='+n);$('msg').textContent=r.msg||''}
async function del(n){if(confirm('Delete '+decodeURIComponent(n)+'?')){await post('/api/delete?name='+n);load()}}
async function ren(n){const t=prompt('New name',decodeURIComponent(n));if(t){const r=await post('/api/rename?from='+n+'&to='+encodeURIComponent(t));$('msg').textContent=r.msg||'';load()}}
async function imp(el){const f=el.files[0];if(!f)return;const r=await post('/api/import',await f.text());$('msg').textContent=r.msg||'';load()}
let learning=false;
async function learnIt(){const n=$('nm').value.trim();if(!n)return $('nm').focus();
 const r=await post('/api/learn?name='+encodeURIComponent(n));if(r.ok===false){$('msg').textContent=r.msg;return}learning=true}
async function poll(){try{const s=await (await fetch('/api/status')).json();
 $('st').textContent=`${s.ip}  |  ${s.rssi} dBm  |  ${s.codes} codes  |  up ${Math.floor(s.uptime_s/60)} min`;
 if(s.last)$('last').textContent=`${s.last.protocol}  ${s.last.bits||''} bit\n${s.last.text||''}`;
 if(s.learning)$('msg').textContent=`Press a key on the remote for "${s.learn_name}" (${Math.ceil(s.learn_left_ms/1000)} s)`;
 else if(learning){learning=false;$('msg').textContent=s.learn_result==='ok'?`Saved "${s.learn_name}"`:'Nothing received - try again closer to the board';load()}
}catch(e){$('st').textContent='offline'}setTimeout(poll,learning?400:2000)}
load();poll();
</script></body></html>)HTML";
