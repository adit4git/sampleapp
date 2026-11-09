
/* =================== Under the hood: the screens themselves ===================
   With the switch on, each part of a screen is labeled by where it comes from:
   ✦ drafted by the model (the inspector shows exactly what it saw), ⚙ calculated by services (no model),
   ▤ published research or the client record (no model). Selecting a label opens the same inspector. */
UH.drafts={};UH.P={};
/* record a lookup that the screen makes directly (the client records), so it shows in the trace like any service */
function uhRec(fn,args,f){const r=f();if(UH.rec&&UH.depth===0)UH.rec.push({fn,args,ret:r});return r}
/* drafts: record what the generator used each time the screen draws it */
for(const[fn,key,label]of[['glanceLede',a=>'glance:'+a[0].id,'Portfolio summary'],['recap',a=>'recap:'+a[0].id+':'+a[1],'Recap: why this opportunity'],['proposalSummary',a=>'prop:'+a[0].id+':'+a[1],'Proposal summary']]){
  const f=window[fn];if(typeof f!=='function')continue;
  window[fn]=function(...a){if(!UH.on||UH.rec)return f.apply(this,a);const calls=[];UH.rec=calls;UH.depth=0;let out;try{out=f.apply(this,a)}finally{UH.rec=null}
    const h=a[0],k=typeof a[1]==='string'?a[1]:null,kk=key(a);if(UH.drafts[kk])delete UH.T[UH.drafts[kk]];
    const tr=uhBuild('draft',null,{kind:k?'workflow':'client',h,k,plain:`${h.name} · ${label}`},calls,/<[a-z]/i.test(out)?out:esc(out));tr.name=label;UH.drafts[kk]=tr.id;return out}}

/* calculated and published parts: run the same services the part uses, and record them */
function uhCalcTrace(spec,h,k){const calls=[];UH.rec=calls;UH.depth=0;try{spec.run(h,k)}catch(e){}finally{UH.rec=null}
  const G=new Map();for(const c of calls){const g=G.get(c.fn)||{fn:c.fn,n:0,hh:new Set(),argv:c.args.map(uhArg),ret:[uhRet(c.fn,c.ret)]};g.n++;g.ks=g.ks||new Set();for(const a of c.args){const x=uhArg(a);if(x&&x.h)g.hh.add(x.h.id);else if(typeof x==='string'&&CK[x])g.ks.add(x)}G.set(c.fn,g)}
  const rules=[],srcs=new Set(spec.src||[]);for(const g of G.values()){const R=UH_RULES[g.fn];if(R){R.r.forEach(x=>rules.push({fn:g.fn,r:x}));if(R.src)srcs.add(SRC[R.src])}}
  if(spec.rule)rules.push({fn:null,r:spec.rule});
  const hs=new Set();for(const g of G.values())g.hh.forEach(x=>hs.add(x));if(h)hs.add(h.id);
  const ent=[...hs].map(byId).filter(x=>x&&x.advisor!==S.adv);
  const C=(name,ok,detail,live=true)=>({name,ok,detail,live});
  const checks=[
   C('No model call',true,spec.kind==='doc'?'Quoted from the published document and the client record. Nothing is sent to a model.':'Calculated by code from the services’ data. Nothing is sent to a model, so there is nothing to tokenize.'),
   C('Permissions',ent.length===0,ent.length?`${ent.length} household(s) outside the book`:hs.size?`${hs.size===1?'The household is':`All ${hs.size} households are`} in ${DATA.advisors[S.adv]}’s book; the services enforce it.`:'No client data.'),
   C(spec.kind==='doc'?'Current version only':'Figures tested on every release',true,spec.kind==='doc'?'The document store serves the latest approved version; the citation names its date and page.':'Golden values for the sample households are checked before each release, like the console’s own test suite.',false),
   C('Audit log',true,'The services log who viewed which household and when, as they do today.',false)];
  const tr={id:'t'+(++UH.n),kind:spec.kind,name:spec.name,what:spec.what,q:null,ctx:{kind:'screen',plain:`${h?h.name+' · ':''}${spec.name}`,h:h&&h.id},G:[...G.values()],rules,srcs:[...srcs],checks,leaks:[],HHs:[...hs]};
  UH.T[tr.id]=tr;return tr}

/* which parts each screen has */
const UH_CIO_SRC=()=>[`CIO House View · ${shortDate(CIO.as_of)}`];
function uhParts(){const p=parse(),r=p[0],h=byId(p[1]),k=p[3],step=+(p[4]||1),out=[],m=document.querySelector('.wf-main');if(!m)return out;
  const q=s=>[...m.querySelectorAll(s)],add=(el,spec)=>{if(el)out.push([el,spec])};
  const calc=(name,what,run,extra={})=>({kind:'calc',name,what,run,...extra});
  if(r==='book'){
    add(m.querySelector('.workstrip'),calc('Pick up where you left off','Your saved progress and reminders, sorted by what is due.',()=>workStrip('book')));
    add(m.querySelector('.heat'),calc('Opportunity tiles','How many clients meet each criterion and how much is involved.',()=>{uhRec('HH',[S.adv],HH);Object.keys(CK).forEach(c=>summary(c))},{rule:'Each tile counts the clients that meet its criterion; thresholds are set by the firm.'}));
    add(m.querySelector('#crit'),calc('Clients for this criterion','The clients that meet the criterion, ranked by amount.',()=>{uhRec('HH',[S.adv],HH);critList(p[1]||S.book.crit)}));
  }
  if(r==='clients')add(q('section.card').find(e=>e.querySelector('.filters')),calc('Client list','Every household with its people, segment, value, return against the benchmark, unrealized gains, cash, next meeting, open work and flags.',()=>{uhRec('HH',[S.adv],HH);viewClients()},{rule:'Sorted and filtered on the page; nothing leaves the browser for that'}));
  if(r==='client'&&h&&!k){
    add(m.querySelector('.chead'),{kind:'doc',name:'Client record',what:'Name, people, entity and segment from the client record. Shown to you; never sent to a model.',run:()=>uhRec('clientRec',[h],()=>h),src:['Client record (CRM)']});
    const az=q('#portfolio .ai-z');add(az.find(e=>/AI-drafted/.test(e.textContent)),{kind:'ai',name:'Portfolio summary',key:'glance:'+h.id,regen:()=>glanceLede(h)});
    add(m.querySelector('.gl-kpis'),calc('Key figures','Return, unrealized gains, cash, largest position and income.',()=>{M(h);GA(h)}));
    add(az.find(e=>/CIO view/.test(e.textContent)),{kind:'doc',name:'CIO view for this client',what:'The house view is quoted from the published CIO document; the alignment score is calculated from the holdings.',run:()=>M(h),src:UH_CIO_SRC()});
    add(m.querySelector('#opps'),calc('Opportunities','What the opportunity engine flags for this household.',()=>opps(h)));
    q('section.card').filter(e=>!e.matches('.chead,#portfolio,#opps')&&!e.closest('#portfolio')).forEach(e=>add(e,calc((e.querySelector('h2,h3')||{}).textContent?.trim()||'Holdings and allocation','Allocation, holdings and drift from the positions service.',()=>{M(h);GA(h)},{src:/CIO/.test(e.textContent)?UH_CIO_SRC():[]})));
  }
  if(r==='client'&&h&&k){
    if(step===1){
      const rs=q('section.wf-sec').find(e=>e.querySelector('.ai-z'));
      if(rs){add(rs.querySelector('.ai-z'),{kind:'ai',name:'Recap: why this opportunity',key:`recap:${h.id}:${k}`,regen:()=>recap(h,k)});
        add(rs.querySelector('.oppg'),calc('The facts behind it','The figures and the rule that flagged this opportunity.',()=>ev(k,h),{rule:CK[k]&&CK[k].rule?CK[k].rule():''}));
        const notes=q('.card.note');if(notes.length)add(notes[0].parentElement.querySelector('.card.note'),calc('Risk, tax and management notes','Risk shift, tax and tax-efficient management for the options.',()=>{allOptions(h,k);if(k==='advisory')advKey(h)}));}
      q('section.wf-sec').filter(e=>e!==rs).forEach(e=>add(e,calc((e.querySelector('h2,h3')||{}).textContent?.trim()||'Details','Where each holding goes and why.',()=>k==='advisory'?advMatrix(h):ev(k,h))));
    }else{
      add(m.querySelector('#strat'),calc('Where the assets go','Strategies ranked by overlap, fit for the gaps, fee and tax.',()=>stratRank(h)));
      add(m.querySelector('#ways'),calc('How to get there','The options, with tax, risk and management figures for each.',()=>allOptions(h,k)));
      add(m.querySelector('.tet'),calc('Tax-efficient transition','Year-by-year schedule within the yearly gain budget.',()=>tetPlan(h,W(h,k).budget||250000,stratOf(h))));
      const rep=m.querySelector('#report');
      if(rep){q('#report > section.rs').forEach(e=>{const t=(e.querySelector('h3')||{}).textContent||'';
        if(e.querySelector('.ai-z'))add(e.querySelector('.ai-z'),{kind:'ai',name:'Proposal summary',key:`prop:${h.id}:${k}`,regen:()=>null});
        else if(/^1\./.test(t))add(e,{kind:'ai',name:'Recap: why we are recommending this',key:`recap:${h.id}:${k}`,regen:()=>recap(h,k)});
        else if(!e.matches('.disc'))add(e,calc(t.replace(/^\d+\.\s*/,'')||'Proposal section','Figures for the chosen option.',()=>{allOptions(h,k);M(h)},{src:/term sheet|transition/i.test(t)?[SRC.ts]:[]}))})}
      q('section.wf-sec').filter(e=>!e.matches('#strat,#ways')&&!e.querySelector('.tet,#report')&&!e.closest('#report')).forEach(e=>add(e,calc((e.querySelector('h2,h3')||{}).textContent?.trim()||'Details','Figures for the selected option.',()=>allOptions(h,k))));
    }
  }
  return out}
const UH_PROV={ai:['✦','Drafted by the model'],calc:['⚙','Calculated · no model'],doc:['▤','Published · no model']};
function uhDecorate(){if(!UH.on)return;const m=document.querySelector('.wf-main');if(!m)return;const parts=uhParts();
  for(const[el,spec]of parts){if(el.dataset.uhp)continue;const id='p'+(++UH.n);UH.P[id]=spec;el.dataset.uhp=spec.kind;el.classList.add('uh-host','uh-'+spec.kind);
    el.insertAdjacentHTML('afterbegin',`<button class="uh-prov ${spec.kind}" data-uhpart="${id}" title="${esc(spec.name)}: see where this comes from"><span aria-hidden="true">${UH_PROV[spec.kind][0]}</span> ${UH_PROV[spec.kind][1]}</button>`)}
  const n={ai:0,calc:0,doc:0};m.querySelectorAll('[data-uhp]').forEach(e=>{if(n[e.dataset.uhp]!=null)n[e.dataset.uhp]++});
  let lg=m.querySelector(':scope > .uh-legend');const html=`<b>Under the hood</b>${n.ai?`<span class="uh-prov ai static">✦ ${n.ai} drafted by the model</span>`:''}${n.calc?`<span class="uh-prov calc static">⚙ ${n.calc} calculated</span>`:''}${n.doc?`<span class="uh-prov doc static">▤ ${n.doc} published</span>`:''}<span class="small muted">Select a label to see where it comes from.</span>`;
  if(!lg){m.insertAdjacentHTML('afterbegin',`<div class="uh-legend" data-uhp="legend">${html}</div>`)}else if(lg.innerHTML!==html)lg.innerHTML=html}
function uhOpenPart(id){const spec=UH.P[id];if(!spec)return;const p=parse(),h=byId(p[1]),k=p[3];let tr;
  if(spec.kind==='ai'){let tid=UH.drafts[spec.key];if(!UH.T[tid]){spec.regen&&spec.regen();tid=UH.drafts[spec.key]}tr=UH.T[tid];if(!tr)return}
  else tr=uhCalcTrace(spec,h,k);
  UH.tab=spec.kind==='ai'?'data':'flow';uhShow(tr.id)}
let uhQ=false;new MutationObserver(()=>{if(!UH.on||uhQ)return;uhQ=true;requestAnimationFrame(()=>{uhQ=false;uhDecorate()})}).observe(document.body,{childList:true,subtree:true});
document.addEventListener('click',e=>{const b=e.target.closest('[data-uhpart]');if(b){e.preventDefault();e.stopPropagation();uhOpenPart(b.dataset.uhpart)}},true);

/* the inspector for calculated and published parts: fewer tabs, and it says plainly that no model is involved */
{const panel=uhPanel;uhPanel=function(){const t=UH.T[UH.open];if(!t||!(t.kind==='calc'||t.kind==='doc'))return panel();
  if(!['flow','svc','guard'].includes(UH.tab))UH.tab='flow';
  const tabs=[['flow','Flow'],['svc','Services and rules'],['guard','Guardrails']];
  return`<div class="uh-h"><div class="uh-ht"><div class="uh-k">Under the hood <span class="small muted">· ${t.kind==='doc'?'published, no model':'calculated, no model'}</span></div><div class="uh-q">${esc(t.name)}</div><div class="small muted">${esc(t.ctx.plain)}</div></div><button class="iconbtn" data-uhclose="1" aria-label="Close">✕</button></div>
   <div class="uh-tabs" role="tablist">${tabs.map(([k,l])=>`<button role="tab" aria-selected="${UH.tab===k}" class="${UH.tab===k?'on':''}" data-uhtab="${k}">${l}</button>`).join('')}</div>
   <div class="uh-b">${UH.tab==='svc'?uhSvcCalc(t):UH.tab==='guard'?uhGuard(t):uhFlowCalc(t)}</div>`}}
function uhFlowCalc(t){const step=(n,h,d,go,st='')=>`<li class="${st}"><span class="uh-n">${n}</span><div><b>${h}</b><div class="small">${d}</div>${go?`<button class="linkbtn small" data-uhtab="${go}">Details</button>`:''}</div></li>`;
  const svc=t.G.length?`${t.G.length} service${t.G.length===1?'':'s'}: ${t.G.slice(0,4).map(g=>esc(UH_API[g.fn][2])).join(', ')}${t.G.length>4?'…':''}.`:t.kind==='doc'?esc(t.srcs.join(', ')):'Read from the screen’s own data.';
  return`<div class="uh-note ${t.kind==='doc'?'':'ok'}"><b>No model involved.</b> ${esc(t.what||'')}</div>
   <ol class="uh-flow">${step(1,'The screen opens','It asks the services for this household’s data, with the advisor’s permissions.',null)}
   ${step(2,t.kind==='doc'?'The document store and client record answer':'Services calculate the figures',svc,'svc','ok')}
   ${step(3,'Shown to you',t.kind==='doc'?'Quoted as published, with the citation. Nothing goes to a model.':'Exactly as calculated. Nothing goes to a model, so no tokens and no gateway.','guard','ok')}</ol>
   <div class="uh-note">Only parts marked ✦ involve the model. Everything else on the screen is calculated or quoted, so it can be tested with fixed expected values.</div>`}
function uhSvcCalc(t){const rows=t.G.map(g=>{const a=UH_API[g.fn],hh=[...g.hh];
  return`<li><div class="uh-api"><span class="uh-m ${a[0]==='GET'?'get':'post'}">${a[0]}</span><code>${esc(a[1].replace('{a}',S.adv).replace('{h}',hh.length===1?hh[0]:'{household}').replace('{k}',g.ks&&g.ks.size>1?'{criterion}':String(g.argv.find(x=>CK[x])||'{criterion}')))}</code></div>
    <div class="small"><b>${esc(a[2])}</b>${hh.length>1?` · ${hh.length} households in one batched request`:''}</div>
    <div class="uh-l" style="margin-top:6px">The screen calls</div><code class="small">${esc(g.fn)}(${esc(g.argv.filter(x=>x!=null).map(x=>x.h?(g.hh.size>1?'each household':x.h.id):g.ks&&g.ks.size>1&&CK[x]?`each of ${g.ks.size} criteria`:String(x)).join(', '))})</code>
    <details><summary class="small">What came back (sample)</summary><pre class="uh-pre">${esc(JSON.stringify(g.ret[0],null,1))}</pre></details></li>`}).join('');
  return`<h4>Services called</h4>${rows?`<ol class="uh-svc">${rows}</ol>`:'<p class="small muted">No service call: this part shows the client record as stored.</p>'}
   <h4>Rules applied</h4>${t.rules.filter(r=>r.r).length?`<ul class="uh-ul">${[...new Map(t.rules.filter(r=>r.r).map(r=>[r.r,r])).values()].map(r=>`<li>${esc(r.r)}${r.fn?` <span class="muted small">· ${esc(UH_API[r.fn][2])}</span>`:''}</li>`).join('')}</ul>`:'<p class="small muted">No program rule involved.</p>'}
   <h4>Sources</h4>${t.srcs.length?`<ul class="uh-ul">${t.srcs.map(s=>`<li>${esc(s)}</li>`).join('')}</ul>`:'<p class="small muted">The firm’s own data services.</p>'}
   <p class="small muted">Paths are illustrative names for the services behind the screens.</p>`}
