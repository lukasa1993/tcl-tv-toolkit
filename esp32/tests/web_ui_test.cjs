// Regression: Start must not look unusable merely because a warning is unchecked.
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const html = fs.readFileSync(__dirname + '/../src/web_page.h', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements = new Map();
function get(id) {
  if (!elements.has(id)) elements.set(id, {value:'0',children:[],checked:false,disabled:false,textContent:''});
  return elements.get(id);
}
const calls=[];let confirmations=0, allow=true;
const context=vm.createContext({URLSearchParams,document:{getElementById:get,querySelectorAll:()=>[]},
  sessionStorage:{getItem:()=>'',setItem:()=>{}},location:{hash:'',pathname:'/'},history:{replaceState:()=>{}},
  setInterval:()=>{},confirm:()=>{confirmations++;return allow},
  fetch:async(path,opts)=>{calls.push({path,opts});return {ok:true,json:async()=>({accepted:true})}},console});
vm.runInContext(script,context);
vm.runInContext("online=true;current={active:false,armed:false};controls()",context);
assert.equal(get('now').disabled,false);assert.equal(get('arm').disabled,false);
vm.runInContext("current.armed=true;controls()",context);
assert.equal(get('now').disabled,true);assert.equal(get('stop').disabled,false);
vm.runInContext("current.armed=false;current.active=true;controls()",context);
assert.equal(get('now').disabled,true);assert.equal(get('stop').disabled,false);
get('steps').children=[{querySelector:selector=>({value:selector==='.command'?'version':'2000'})}];
(async()=>{
  await vm.runInContext("start('now')",context);
  assert.equal(confirmations,0);assert.equal(calls.at(-1).opts.body.get('risk'),'ack');
  get('steps').children=[{querySelector:selector=>({value:selector==='.command'?'env set devicestate unlock':'2000'})}];
  allow=false;const before=calls.length;
  await vm.runInContext("start('now')",context);
  assert.equal(confirmations,1);assert.equal(calls.length,before);
  allow=true;await vm.runInContext("start('arm')",context);
  assert.equal(confirmations,2);assert.equal(calls.at(-1).opts.body.get('risk'),'ack');
  assert.equal(calls.at(-1).opts.body.get('mode'),'arm');
  get('risk').checked=false;await vm.runInContext("start('dry')",context);
  assert.equal(confirmations,2);assert.equal(calls.at(-1).opts.body.get('mode'),'dry');
  console.log('PASS: Start enabled while disarmed; STOP available when armed/running; harmless commands start directly; changing commands warn; cancel sends nothing; dry run needs no acknowledgment.');
})().catch(e=>{console.error(e);process.exitCode=1});
