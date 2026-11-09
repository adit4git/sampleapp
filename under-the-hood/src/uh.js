
/* =================== Under the hood ===================
   A switch in the top bar. When it is on, every Ask Atlas answer carries a strip that opens an inspector:
   what the services retrieved, what the gateway would send to the model (tokens, not names), which services,
   rules and documents were used, which guardrails ran, and which evals cover it.
   Prototype: no model is called. Answers still come from rules; the payload is what a gateway would send.
   The guardrail checks (leak check, output scan, name restoration) really run on each answer, in this page. */
const UH={on:false,rec:null,depth:0,T:{},n:0,tab:'flow',open:null,sweep:null,det:null};
try{UH.on=localStorage.getItem('atlas-uh')==='1'}catch(e){}

/* ---- the services each call stands for in production ---- */
const UH_API={
 HH:['GET','/advisors/{a}/households','Client records (CRM)'],
 clientRec:['GET','/households/{h}','Client records (CRM)'],
 M:['GET','/households/{h}/positions','Positions and balances'],
 GA:['GET','/households/{h}/analytics','Portfolio analytics'],
 opps:['GET','/households/{h}/opportunities','Opportunity engine'],
 ev:['GET','/opportunities/{k}/households/{h}','Opportunity engine'],
 summary:['GET','/book/opportunities/{k}','Opportunity engine (book)'],
 latestProposal:['GET','/households/{h}/proposals','Proposals'],
 advElig:['POST','/advisory/eligibility','Eligibility rules'],
 advMatrix:['POST','/advisory/conversion-routes','Conversion rules'],
 allOptions:['POST','/proposals/options','Proposal engine'],
 advKey:['POST','/analytics/risk-tax-shift','Risk and tax analytics'],
 annualCost:['GET','/billing/cost-estimate','Fee and cost estimator'],
 tetPlan:['POST','/tax/transition-plan','Transition model'],
 stratRank:['GET','/strategies/fit','Strategy catalog'],
 stratEval:['GET','/strategies/fit','Strategy catalog'],
 scoreOptions:['POST','/guide/score-options','Decision guide scoring'],
 guideStrategy:['POST','/guide/strategy','Decision guide scoring'],
 kbAnswer:['POST','/documents/search','Approved document search'],
 cioAnswer:['GET','/research/cio-house-view','Research documents'],
 workItems:['GET','/work-items','Work queue'],
 reminderFromText:['POST','/reminders','Reminders (writes)'],
};
const UH_RULES={
 advElig:{src:'cv',r:['Largest single stock above 50% of the household → specialist review','No cost basis → held until Operations finds it','Insider stock → Compliance pre-clearance','Excluded assets stay in brokerage']},
 advMatrix:{src:'cv',r:['Each brokerage holding takes the first of 9 routes that applies']},
 allOptions:{r:['Wash-sale rule: no option buys back a fund sold at a loss within 30 days','Tax at 23.8% on net realized long-term gains']},
 advKey:{r:['Risk shift: tracking error, largest drift, volatility, stress scenario','Tax at 23.8% on net realized long-term gains']},
 annualCost:{src:'br',r:['Program fee: advisory fee (maximum 1.75% a year) plus any manager fee']},
 tetPlan:{src:'ts',r:['Yearly net long-term gain budget; short-term budget $0','Each year: losses first, then the lowest gain per dollar','Bonds and CDs outside the budget; lots without basis not eligible']},
 stratRank:{r:['Strategy fit: overlap with what the client holds, fit for the gaps, fee, tax to get there']},
 stratEval:{r:['Strategy fit: overlap with what the client holds, fit for the gaps, fee, tax to get there']},
 scoreOptions:{r:['Options scored on the client’s answers: tax tolerance, who decides, cash needs, risk']},
 guideStrategy:{r:['Strategy weighted by what should lead: keep holdings, fit the gaps, lowest fee or the CIO model']},
 summary:{r:[]},ev:{r:['Each household is checked against the firm’s 13 opportunity criteria; a flag shows for each one it meets']},
 HH:{r:['Only households where this advisor is the advisor of record']},
};

/* ---- record the service calls an answer makes (top level only; what a service does inside stays inside) ---- */
for(const name of Object.keys(UH_API)){const f=window[name];if(typeof f!=='function')continue;
  window[name]=function(...a){if(!UH.rec)return f.apply(this,a);UH.depth++;let r;try{r=f.apply(this,a)}finally{UH.depth--}
    if(UH.depth===0)UH.rec.push({fn:name,args:a,ret:r});return r}}

/* ---- synthetic identifiers: what a client record holds in a system of record (made up, fictional ranges) ---- */
const uhHash=s=>{let x=2166136261;for(const c of s)x=Math.imul(x^c.charCodeAt(0),16777619);return x>>>0};
const UH_GENERIC=/^(the|family|trust|household|holdings|llc|foundation|living|revocable|irrevocable|board|of|trustees|chair|trustee)$/i;
function uhPersons(h){let c=(h.contact||'').replace(/^Board( of Trustees)?\s*[—-]?\s*/,'');
  const par=(c.match(/\(([^)]*)\)/)||[])[1]||'';c=c.replace(/\([^)]*\)/g,'').trim();if(!c)c=par.split(',')[0].trim();
  const parts=c.split(/\s*&\s*/).map(s=>s.trim()).filter(Boolean),sur=(parts[parts.length-1]||'').split(/\s+/).slice(1).join(' ');
  return parts.map(p=>p.split(/\s+/).length===1&&sur?p+' '+sur:p)}
function uhPII(h){const r=uhHash(h.id),d=n=>String(uhHash(h.id+n)%10);
  const P=uhPersons(h),first=(P[0]||'client').split(/\s+/)[0],last=(P[0]||'').split(/\s+/).slice(-1)[0]||h.id;
  const streets=['Linden Lane','Harbor View Road','Oak Hollow Drive','Mill Pond Court','Cedar Ridge Way','Bayberry Street','Old Post Road','Willow Bend Avenue'];
  const accts=[...new Set(h.holdings.map(x=>x.acct))].map((a,i)=>({type:a==='BRK'?'Brokerage':'Advisory program',code:a,no:`${'4K7X9QH2'[r%8]}${'XQZJMW'[(r>>>3)%6]}${i+1}-${String(10000+uhHash(h.id+a)%89999)}`}));
  const ins=h.holdings.find(x=>x.insider);
  return{persons:P,address:`${100+r%880} ${streets[r%8]}, Springfield 0${String(r%9000+1000)}`,phone:`(617) 555-01${d(1)}${d(2)}`,
    email:`${first}.${last}`.toLowerCase().replace(/ø/g,'o').replace(/æ/g,'ae').normalize('NFD').replace(/[^\x00-\x7f]/g,'').replace(/[^a-z.]/g,'').replace(/\.+/g,'.')+'@example.com',
    dob:`${1946+r%30}-${String(1+(r>>>5)%12).padStart(2,'0')}-${String(1+(r>>>9)%28).padStart(2,'0')}`,
    tin:`9${d(3)}${d(4)}-${7+r%2}${d(5)}-${d(6)}${d(7)}${d(8)}${d(9)}`,accts,employer:ins?`${SEC[ins.sym]?.name||ins.sym} (insider)`:null}}

/* ---- tokens: one table per session; the model sees tokens, names come back only on screen ---- */
const UH_TOK={m:new Map(),c:{CLIENT:0,PERSON:0,ACCT:0}};
const uhTok=(kind,key)=>{const k=kind+':'+key;if(!UH_TOK.m.has(k))UH_TOK.m.set(k,`${kind}_${++UH_TOK.c[kind]}`);return UH_TOK.m.get(k)};
const uhRx=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
let UH_DICT=null;
function uhDict(){if(UH_DICT)return UH_DICT;const L=[];const cs=new Set();
  for(const h of DATA.households){const tk=()=>uhTok('CLIENT',h.id);L.push([h.name,tk]);const sn=shortName(h);if(sn.length>2)L.push([sn,tk]);
    for(const w of h.name.split(/\s+/))if(w.length>2&&!UH_GENERIC.test(w)&&w!==sn)L.push([w,tk]);
    for(const p of uhPersons(h)){const pk=()=>uhTok('PERSON',p);L.push([p,pk]);const fn=p.split(/\s+/)[0];if(fn.length>2&&!/\./.test(fn)){L.push([fn,pk]);cs.add(fn)}}
    for(const a of uhPII(h).accts)L.push([a.no,()=>uhTok('ACCT',a.no)])}
  L.sort((a,b)=>b[0].length-a[0].length);
  UH_DICT=L.map(([s,f])=>[new RegExp(`(?<![\\p{L}\\p{N}])${uhRx(s)}(?![\\p{L}\\p{N}])`,cs.has(s)?'gu':'giu'),f,s]);/* first names alone match only when capitalized (Grant, not grant) */return UH_DICT}
/* patterns for identifiers typed or written in free text */
const UH_PAT=[
 ['SSN or tax ID',/\b\d{3}-\d{2}-\d{4}\b/g],
 ['Email',/\b[\w.+-]+@[\w-]+\.[\w.]+\b/g],
 ['Phone',/(?:\+?1[\s.-]?)?\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b|\b555-01\d\d\b/g],
 ['Account number',/\b[A-Z0-9]{3}-\d{5}\b|\b(?:acct|account)\s*(?:no\.?|number|#)?\s*:?\s*\d[\d-]{5,}\b/gi],
 ['Date of birth',/\b(?:19|20)\d{2}-\d{2}-\d{2}\b|\b\d{1,2}\/\d{1,2}\/(?:19|20)\d{2}\b/g],
 ['Street address',/\b\d{1,5}\s+(?:[A-Z][a-z]+\s){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Way|Boulevard|Blvd)\b\.?/g],
];
/* returns the redacted text and what was found */
function uhRedact(text){let t=String(text??'');const found=[];
  for(const[label,re]of UH_PAT)t=t.replace(re,m=>{found.push({type:label,v:m});return`[${label.toUpperCase().replace(/ /g,'_')}_REMOVED]`});
  for(const[re,tk,s]of uhDict())t=t.replace(re,m=>{const k=tk();found.push({type:k.startsWith('CLIENT')?'Client name':k.startsWith('ACCT')?'Account number':'Person name',v:m,tok:k});return k});
  return{t,found}}

/* ---- summaries of what a service returned, sent through the same redaction ---- */
const uhArg=a=>{if(!a||typeof a!=='object')return a;if(a.holdings)return{h:a};if(a.id)return String(a.id);if(Array.isArray(a))return`[${a.length}]`;const j=JSON.stringify(a);return j&&j.length<=90&&Object.values(a).every(v=>v==null||typeof v!=='object')?j:'{…}'};
const uhDec=s=>{const d=document.createElement('textarea');d.innerHTML=s;return d.value};
function uhRet(fn,r){
  const rd=v=>typeof v==='string'?uhRedact(v.replace(/<[^>]+>/g,'')).t:v,n=v=>typeof v==='number'?Math.round(v*100)/100:v;
  try{switch(fn){
   case'M':return{value:n(r.aum),weights:Object.fromEntries(Object.entries(r.w||{}).map(([k,v])=>[k,n(v)])),target:Object.fromEntries(Object.entries(r.t||{}).map(([k,v])=>[k,n(v)])),unrealized_loss:n(r.loss)};
   case'tetPlan':return{budget:r.budget,years:r.n,transition_assets:Math.round(r.start),net_gains:Math.round(r.gross),year1_tax:Math.round(r.years[0]?.tax||0),without_service_tax:Math.round(r.without.tax),eligible:r.eligible};
   case'summary':return{households:r.n,of:r.book,value:Math.round(r.v),top:r.hit.slice(0,5).map(([h,e])=>({client:uhTok('CLIENT',h.id),value:Math.round(e.v)}))};
   case'ev':return r?{value:Math.round(r.v)}:null;
   case'opps':return r.slice(0,6).map(o=>({id:o.k,title:rd(o.title)}));
   case'advElig':return{status:r.status,label:rd(r.label),conditions:(r.conds||[]).length};
   case'advMatrix':return{routes:Object.fromEntries(Object.entries(r.tot||{}).map(([k,v])=>[k,Math.round(v)]))};
   case'allOptions':return{options:(r.O||[]).map(o=>({id:o.id,title:rd(o.title),tax:Math.round(o.km?.tax||0)}))};
   case'advKey':return{option:rd(r.title||''),tax:Math.round(r.tax||0),tracking_error:[n(r.a?.te),n(r.b?.te)]};
   case'annualCost':return{today_per_year:Math.round(r.total||0)};
   case'kbAnswer':return r?{passage:rd(r).slice(0,220)+(rd(r).length>220?'…':'')}:{passage:null};
   case'cioAnswer':return{passage:rd(r).slice(0,180)+'…'};
   case'HH':return{households:r.length,fields:['name','people','entity','segment','client since','return this year','next meeting']};
   case'clientRec':return{household:uhTok('CLIENT',r.id),fields:['name','people','entity','segment','client since']};
   case'workItems':return{items:r.length,due:r.filter(x=>x.due).length};
   case'GA':return{tracking_error:n(r.te),volatility:n(r.vol)};
   case'stratRank':case'stratEval':return Array.isArray(r)?r.slice(0,3).map(x=>({strategy:rd(x.st?.name||x.name||x.id||''),score:n(x.score)})):{strategy:rd(r?.st?.name||'')};
   case'scoreOptions':return r.slice(0,3).map(x=>({option:rd(x.o.title),score:n(x.s??x.score)}));
   default:if(r==null)return null;if(typeof r!=='object')return rd(r);return Object.fromEntries(Object.entries(r).filter(([,v])=>['number','string','boolean'].includes(typeof v)).slice(0,6).map(([k,v])=>[k,rd(n(v))]))}}
  catch(e){return'(summary unavailable)'}}

/* ---- build the trace for one answer ---- */
function uhCapture(fn){UH.rec=[];UH.depth=0;let out;try{out=fn()}finally{UH.last=UH.rec;UH.rec=null}return out}
function uhBuild(kind,q,ctx,calls,html){
  const id='t'+(++UH.n),text=uhDec(String(html||'').replace(/<li>/g,' • ').replace(/<br\s*\/?>|<\/(li|ul|ol|div|p|blockquote)>/g,' ').replace(/<[^>]+>/g,'')).replace(/\s+/g,' ').trim();
  /* group the calls by service */
  const G=new Map();for(const c of calls){if(c.fn==='kbAnswer'&&!c.ret)continue;const g=G.get(c.fn)||{fn:c.fn,n:0,hh:new Set(),args:[],ret:[],argv:c.args.map(uhArg)};g.n++;
    for(const a of c.args){const x=uhArg(a);if(x&&x.h)g.hh.add(x.h.id);else if(x!=null&&g.args.length<3&&!g.args.includes(x))g.args.push(x)}
    if(g.ret.length<1)g.ret.push(uhRet(c.fn,c.ret));G.set(c.fn,g)}
  /* households retrieved: from the calls, the screen, and those named in the answer */
  const hs=new Set();for(const g of G.values())g.hh.forEach(x=>hs.add(x));if(ctx&&ctx.h)hs.add(ctx.h.id);
  for(const h of DATA.households)if(text.includes(h.name))hs.add(h.id);
  const HHs=[...hs].map(byId).filter(Boolean),focus=ctx&&ctx.h?[ctx.h]:HHs.length===1?HHs:HHs.filter(h=>text.includes(h.name)).slice(0,1);
  /* the question as typed, and as sent */
  const qr=uhRedact(q||'');
  /* field by field: retrieved vs sent, with the rule applied */
  const rows=[];
  for(const h of focus){const P=uhPII(h),ct=uhTok('CLIENT',h.id),age=Math.floor((ASOF-new Date(P.dob))/3.156e10),band=`${Math.floor(age/10)*10}–${Math.floor(age/10)*10+9}`;
    const notes=[h.notes,h.nextMeeting&&h.nextMeeting.note].filter(Boolean).join(' '),nr=uhRedact(notes);
    const R=(f,v,s,rule)=>rows.push({h:h.id,f,v,s,rule});
    R('Household name',h.name,ct,'tokenized');
    P.persons.forEach((p,i)=>R(i?'Second person':'Primary contact',p,uhTok('PERSON',p),'tokenized'));
    R('Tax ID',P.tin,null,'removed');R('Date of birth',P.dob,`age ${band}`,'generalized');
    R('Home address',P.address,null,'removed');R('Phone',P.phone,null,'removed');R('Email',P.email,null,'removed');
    P.accts.forEach(a=>R(`${a.type} account no.`,a.no,`${uhTok('ACCT',a.no)} (${a.type.toLowerCase()})`,'tokenized'));
    if(P.employer)R('Employer',P.employer,'insider: yes','generalized');
    R('Entity and segment',`${h.entity} · ${h.segment}`,`${h.entity} · ${h.segment}`,'allowed');
    R('Risk profile and target',`${h.risk} · ${Object.entries(h.target).map(([k,v])=>k+' '+v+'%').join(', ')}`,'same','allowed');
    R('Positions',`${h.holdings.length} lots · ${money(h.holdings.reduce((a,x)=>a+x.mv,0))}`,'same (symbol, value, cost, account token)','allowed');
    if(notes)R('Advisor notes (free text)',notes,nr.t,nr.found.length?'redacted':'allowed');}
  /* the payload the gateway would send */
  const sys='You are Ask Atlas, an assistant for financial advisors. Answer only from the tool results and documents provided. Never calculate tax or risk yourself: call the services. Refer to clients only by their tokens. Cite the document for every program rule.';
  const prof=h=>{const P=uhPII(h),ct=uhTok('CLIENT',h.id),age=Math.floor((ASOF-new Date(P.dob))/3.156e10);
    return{client:ct,people:P.persons.map(p=>uhTok('PERSON',p)),age_band:`${Math.floor(age/10)*10}s`,entity:h.entity,segment:h.segment,risk_profile:h.risk,target:h.target,
      accounts:P.accts.map(a=>({account:uhTok('ACCT',a.no),type:a.type})),insider:!!P.employer||undefined,
      positions:h.holdings.slice(0,8).map(x=>({sym:x.sym,value:x.mv,cost:x.cost,account:uhTok('ACCT',(P.accts.find(a=>a.code===x.acct)||P.accts[0]).no)})).concat(h.holdings.length>8?[`…${h.holdings.length-8} more`]:[]),
      notes:uhRedact([h.notes,h.nextMeeting&&h.nextMeeting.note].filter(Boolean).join(' ')).t||undefined}};
  const sctx=ctx?{screen:ctx.kind,client:ctx.h?uhTok('CLIENT',ctx.h.id):undefined,criterion:ctx.k||undefined,level:ctx.lvl||undefined,filter:ctx.f?uhRedact(ctx.f).t:undefined,step:kind==='wf'?(+(parse()[4]||1)):undefined,opportunity:ctx.k&&ctx.kind==='wf'?ctx.k:undefined}:{screen:'ask'};
  const tools=[...G.values()].map(g=>({tool:g.fn,args:[...[...g.hh].map(x=>uhTok('CLIENT',x)),...g.args.map(a=>typeof a==='string'?uhRedact(a).t:a)],calls:g.n,result:g.ret[0]}));
  const payload={system:sys,context:sctx,clients:focus.map(prof),others:HHs.filter(h=>!focus.includes(h)).slice(0,12).map(h=>uhTok('CLIENT',h.id)).concat(HHs.length-focus.length>12?[`…${HHs.length-focus.length-12} more`]:[]),tool_results:tools,question:q?qr.t:`(no question: ${kind==='opener'?'Atlas opens this screen with a point of view':kind==='draft'?'Atlas drafts this text for the screen, for the advisor to review':'the decision guide asks for its recommendation'})`};
  const pj=JSON.stringify(payload,null,1);
  /* the model's answer in tokens, and the answer shown with names restored */
  const raw=uhRedact(text).t;
  /* checks that really run here */
  const ids=[];for(const h of HHs){const P=uhPII(h);ids.push(h.name,shortName(h),...P.persons,P.tin,P.dob,P.address,P.phone,P.email,...P.accts.map(a=>a.no));if(P.employer)ids.push(P.employer)}
  const leaks=[...new Set(ids)].filter(v=>v&&v.length>2&&new RegExp(`(?<![\\p{L}\\p{N}])${uhRx(v)}(?![\\p{L}\\p{N}])`,'iu').test(pj));
  const outFound=UH_PAT.flatMap(([l,re])=>(raw.match(re)||[]).map(v=>({type:l,v})));
  const known=new Set(UH_TOK.m.values()),toks=[...new Set(raw.match(/\b(CLIENT|PERSON|ACCT)_\d+\b/g)||[])],stray=toks.filter(x=>!known.has(x));
  const sentToks=new Set(pj.match(/\b(CLIENT|PERSON|ACCT)_\d+\b/g)||[]),foreign=toks.filter(x=>!sentToks.has(x));
  const shown=text,leftTok=/\b(CLIENT|PERSON|ACCT)_\d+\b/.test(shown);
  const ent=HHs.filter(h=>h.advisor!==S.adv);
  const inj=[...HHs.map(h=>h.notes||''),...[...G.values()].flatMap(g=>g.ret.map(x=>JSON.stringify(x)))].filter(s=>/ignore (all |the )?(previous|prior) instructions|system prompt|disregard the rules/i.test(s));
  const writes=[...G.keys()].filter(f=>f==='reminderFromText').length+(/set (the )?budget|budget to/i.test(q||'')?1:0);
  const conc=focus.filter(h=>{const t=h.holdings.reduce((a,x)=>a+x.mv,0),by={};for(const x of h.holdings)by[x.sym]=(by[x.sym]||0)+x.mv;return Object.values(by).some(v=>v/t>.2)||h.holdings.some(x=>x.insider)});
  const C=(name,ok,detail,live=true)=>({name,ok,detail,live});const pl=(n,w,ws)=>`${n} ${n===1?w:(ws||w+'s')}`;
  const checks=[
   C('Names resolved by the app',true,`${qr.found.filter(f=>f.tok).length?qr.found.filter(f=>f.tok).map(f=>`“${f.v}” → ${f.tok}`).join(', '):'No names in the question'}; the screen’s context carries IDs only.`),
   C('Permissions',ent.length===0,ent.length?`${pl(ent.length,'household')} outside this advisor’s book`:HHs.length?`${HHs.length===1?'The household is':`All ${HHs.length} households are`} in ${DATA.advisors[S.adv]}’s book; the services check this, not the prompt.`:'No household data in this answer.'),
   C('Approved fields only',true,`${rows.filter(r=>r.rule==='removed').length} removed, ${rows.filter(r=>r.rule==='tokenized').length} tokenized, ${rows.filter(r=>r.rule==='generalized').length} generalized, ${rows.filter(r=>r.rule==='allowed'||r.rule==='redacted').length} allowed.`),
   C('Free text checked',true,`Question: ${qr.found.filter(f=>!f.tok).length?qr.found.filter(f=>!f.tok).map(f=>f.type).join(', ')+' removed':'no identifiers'}. Notes: ${rows.filter(r=>r.rule==='redacted').length?'names redacted':'nothing to redact'}.`),
   C('Instructions hidden in retrieved text',inj.length===0,inj.length?`${pl(inj.length,'suspicious passage')} blocked`:'None found in notes or service results.'),
   C('Leak check on the payload',leaks.length===0,leaks.length?`Found: ${leaks.join(', ')}`:`0 of ${new Set(ids).size} identifiers from ${pl(HHs.length,'household')} appear in what would be sent.`),
   C('Answer scanned on the way back',outFound.length===0,outFound.length?outFound.map(f=>f.type).join(', '):'No SSNs, phones, emails, account numbers or addresses.'),
   C('Tokens belong to this request',stray.length===0&&foreign.length===0,stray.length||foreign.length?`Unexpected: ${[...stray,...foreign].join(', ')}`:toks.length?`${pl(toks.length,'token')} in the answer, all from this request.`:'No tokens in the answer.'),
   C('Names restored on screen only',!leftTok,leftTok?'A token is still visible':'The model never sees the token table; the page swaps tokens back for display.'),
   C('Figures come from services',true,`${pl(G.size,'service result')} supplied; the instructions forbid the model from calculating.`,false),
  ];
  if(writes)checks.push(C('Changes need the advisor’s confirmation',true,'This request changes something (a reminder or the budget). In production the model proposes it and the advisor confirms; the prototype applies it directly.',false));
  /* rules and sources */
  const rules=[],srcs=new Set();for(const g of G.values()){const R=UH_RULES[g.fn];if(R){R.r.forEach(x=>rules.push({fn:g.fn,r:x}));if(R.src)srcs.add(SRC[R.src])}
    if(g.fn==='summary'||g.fn==='ev'){for(const a of g.args)if(CK[a])rules.push({fn:g.fn,r:`Criterion “${CK[a].label}”${a==='maturing'?`: ${money(S.book.minMat)}+, next ${S.book.horizon} months`:''}`})}}
  for(const m of String(html).matchAll(/class="kb-src">Source: ([^<]+)</g))srcs.add(m[1]);
  for(const m of String(html).matchAll(/class="cite"[^>]*data-cite="(\d+)"[^>]*>(?:<[^>]+>[^<]*<\/[^>]+>)?([^<]+)/g))srcs.add(`${m[2].replace(/\s*↗\s*$/,'').trim()} (opens the PDF)`);
  const tr={id,kind,q,ctx:ctx?{kind:ctx.kind,plain:ctx.plain||String(ctx.line||'').replace(/<[^>]+>/g,''),h:ctx.h&&ctx.h.id,k:ctx.k,lvl:ctx.lvl,f:ctx.f}:{kind:'ask'},
    G:[...G.values()],HHs:HHs.map(h=>h.id),focus:focus.map(h=>h.id),rows,qr,payload,pj,raw,shown,checks,rules,srcs:[...srcs],leaks,conc:conc.map(h=>h.id),nIds:new Set(ids).size,writes};
  UH.T[id]=tr;return tr}

/* ---- attach traces to the answers ---- */
function uhRun(kind,q,ctx,fn){const out=uhCapture(fn);const html=typeof out==='string'?out:out?(out.html||esc(out.text||'')):'';return{out,tr:uhBuild(kind,q,ctx,UH.last,html)}}
ask=function(q){
  if(!q.trim())return;
  S.chat.push({who:'u',text:q});S.chat.push({typing:true});paintStream();
  const{out:r,tr}=uhRun('panel',q,ctxOf(),()=>atlasAnswer(q));
  setTimeout(()=>{S.chat.pop();S.chat.push({who:'a',text:r.text,html:r.html,acts:r.acts,tr:tr.id});paintStream();if(r.nav)setTimeout(()=>go(r.nav),550)},380);
};
wfAsk=function(q){const p=parse(),h=byId(p[1]),k=p[3];if(!q.trim()||!h)return;const w=W(h,k);w.chat.push({who:'u',text:q});w.chat.push({typing:true});paintWf(h,k);
  const c=ctxOf();setTimeout(()=>{w.chat.pop();const{out,tr}=uhRun('wf',q,c,()=>wfAnswer(h,k,q));w.chat.push({who:'a',html:out,tr:tr.id});paintWf(h,k)},350)};
atlasStep=function(c){
  if(!['book','clients','client'].includes(c.kind)||S.lastCtx===c.key)return;
  S.lastCtx=c.key;const{out:m,tr}=uhRun('opener',null,c,()=>opener(c));if(!m)return;
  const last=S.chat[S.chat.length-1];if(last&&last.auto)S.chat.pop();
  S.chat.push({who:'a',auto:true,ctx:c.plain,html:m.html,acts:m.acts,tr:tr.id});S.railNew=true;
};
{const gr=guideRecommend;guideRecommend=function(h,k){const w=W(h,k),n=w.chat.length,c=ctxOf();const out=uhCapture(()=>gr(h,k));
  const m=w.chat.slice(n).reverse().find(x=>x.who==='a'&&x.html);if(m)m.tr=uhBuild('guide',null,c,UH.last,m.html).id;return out}}
{const mh=msgHtml;msgHtml=function(m){const s=mh(m);return m.tr&&UH.on&&UH.T[m.tr]?s.replace(/<\/div>$/,uhStrip(m.tr)+'</div>'):s}}
{const wh=wfMsgHtml;wfMsgHtml=function(m,i,l){const s=wh(m,i,l);return m.tr&&UH.on&&UH.T[m.tr]?s.replace(/<\/div>$/,uhStrip(m.tr)+'</div>'):s}}
function uhStrip(id){const t=UH.T[id],ok=t.checks.filter(c=>c.live&&c.ok).length,all=t.checks.filter(c=>c.live).length;
  return`<button class="uh-strip" data-uh="${id}" title="See what Atlas retrieved and what the model would see"><span class="uh-ic" aria-hidden="true">⚙</span><span>${t.G.length} service${t.G.length===1?'':'s'}</span><span>${t.srcs.length} source${t.srcs.length===1?'':'s'}</span><span class="${ok===all?'ok':'bad'}">${ok}/${all} checks</span><span class="${t.leaks.length?'bad':'ok'}">${t.leaks.length?t.leaks.length+' identifiers sent':'0 identifiers sent'}</span></button>`}

/* ---- the inspector ---- */
const UH_TABS=[['flow','Flow'],['data','Data'],['prompt','Prompt'],['svc','Services and rules'],['guard','Guardrails'],['evals','Evals']];
const uhRule=r=>`<span class="uh-rule ${r}">${{removed:'Removed',tokenized:'Tokenized',generalized:'Generalized',allowed:'Allowed',redacted:'Redacted'}[r]}</span>`;
const uhHi=s=>esc(s).replace(/\b(CLIENT|PERSON|ACCT)_\d+\b/g,'<mark class="tok">$&</mark>').replace(/\[[A-Z_]+_REMOVED\]/g,'<mark class="rm">$&</mark>');
function uhPanel(){const t=UH.T[UH.open];if(!t)return'';
  const title=t.q?`“${esc(t.q)}”`:t.kind==='draft'?`✦ Drafted by the model · ${esc(t.name||'')}`:t.kind==='opener'?`Opening message · ${esc(t.ctx.plain||'')}`:'Decision guide recommendation';
  return`<div class="uh-h"><div class="uh-ht"><div class="uh-k">Under the hood <span class="small muted">· simulated: no model is called</span></div><div class="uh-q">${title}</div><div class="small muted">${esc(t.ctx.plain||'Ask Atlas')}</div></div><button class="iconbtn" data-uhclose="1" aria-label="Close">✕</button></div>
   <div class="uh-tabs" role="tablist">${UH_TABS.map(([k,l])=>`<button role="tab" aria-selected="${UH.tab===k}" class="${UH.tab===k?'on':''}" data-uhtab="${k}">${l}</button>`).join('')}</div>
   <div class="uh-b">${({flow:uhFlow,data:uhData,prompt:uhPrompt,svc:uhSvc,guard:uhGuard,evals:uhEvals}[UH.tab]||uhFlow)(t)}</div>`}
function uhFlow(t){const rm=t.rows.filter(r=>r.rule==='removed').length,tk=t.rows.filter(r=>r.rule==='tokenized').length,ok=t.checks.filter(c=>c.live&&c.ok).length,all=t.checks.filter(c=>c.live).length;
  const step=(n,h,d,go,st='')=>`<li class="${st}"><span class="uh-n">${n}</span><div><b>${h}</b><div class="small">${d}</div>${go?`<button class="linkbtn small" data-uhtab="${go}">Details</button>`:''}</div></li>`;
  return`<ol class="uh-flow">
   ${step(1,t.q?'The advisor asks':'The screen opens',t.q?`“${esc(t.q)}”`:esc(t.ctx.plain||''),null)}
   ${step(2,'The screen says what it shows',`Context record: ${esc(t.ctx.kind)}${t.ctx.h?' · household '+esc(t.ctx.h):''}${t.ctx.k?' · '+esc(t.ctx.k):''}${t.ctx.lvl?' · '+esc(t.ctx.lvl):''}. IDs, not names.`,'data')}
   ${step(3,'Services retrieve the data',`${t.G.length} service${t.G.length===1?'':'s'}: ${t.G.slice(0,4).map(g=>esc(UH_API[g.fn][2])).join(', ')}${t.G.length>4?'…':''}. ${t.HHs.length} household${t.HHs.length===1?'':'s'} touched.`,'svc')}
   ${step(4,'The gateway prepares the request',`${rm} identifiers removed, ${tk} tokenized${t.qr.found.length?`, ${t.qr.found.length} found in the question`:''}. Leak check: ${t.leaks.length?'<b class="neg">failed</b>':'<b class="pos">0 identifiers</b>'}.`,'data',t.leaks.length?'bad':'ok')}
   ${step(5,'The model writes the answer',`It sees tokens such as ${esc([...new Set(t.pj.match(/\b(CLIENT|PERSON|ACCT)_\d+\b/g)||[])].slice(0,3).join(', ')||'none')} and the service results, never names or account numbers.`,'prompt')}
   ${step(6,'The answer is checked',`${ok} of ${all} checks passed${t.srcs.length?`; ${t.srcs.length} source${t.srcs.length===1?'':'s'} cited`:''}.`,'guard',ok===all?'ok':'bad')}
   ${step(7,'Names come back on your screen only','The page swaps tokens for names. The token table never leaves the firm.','prompt')}
  </ol>
  <div class="uh-note">Prototype: answers still come from rules over the sample book. Everything here is what a production gateway would send and check. Steps 4 and 6 really run on this answer. Identifiers are made up (555 phone numbers, example.com email, tax IDs starting with 9).</div>`}
function uhData(t){const H=t.focus.map(byId);
  const q=t.q?`<h4>Your question</h4><div class="uh-2"><div><div class="uh-l">As typed</div><div class="uh-box">${esc(t.q)}</div></div><div><div class="uh-l">As sent</div><div class="uh-box">${uhHi(t.qr.t)}</div></div></div>${t.qr.found.length?`<div class="small muted">Found: ${t.qr.found.map(f=>`${esc(f.type)} “${esc(f.v)}”`).join(', ')}</div>`:''}`:'';
  const ctx=`<h4>What the screen published</h4><table class="uh-t"><thead><tr><th>Field</th><th>On the screen</th><th>Sent</th></tr></thead><tbody>${Object.entries(t.payload.context).filter(([,v])=>v!==undefined).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${k==='client'?esc(byId(t.ctx.h)?.name||''):esc(String(v))}</td><td>${uhHi(String(v))}</td></tr>`).join('')}</tbody></table>`;
  const tbl=H.length?H.map(h=>`<h4>${esc(h.name)}: retrieved vs sent</h4><table class="uh-t"><thead><tr><th>Field</th><th>Retrieved</th><th>Sent to the model</th><th>Rule</th></tr></thead><tbody>${t.rows.filter(r=>r.h===h.id).map(r=>`<tr class="r-${r.rule}"><td>${esc(r.f)}</td><td>${esc(r.v)}</td><td>${r.s==null?'<span class="muted">not sent</span>':r.s==='same'?'<span class="muted">same</span>':uhHi(r.s)}</td><td>${uhRule(r.rule)}</td></tr>`).join('')}</tbody></table>`).join(''):'<p class="small muted">No single household is in focus for this answer.</p>';
  const others=t.HHs.length>H.length?`<p class="small">${t.HHs.length-H.length} more household${t.HHs.length-H.length===1?'':'s'} touched by the services: the model gets only their tokens and the figures it needs (for example ${t.HHs.filter(x=>!t.focus.includes(x)).slice(0,3).map(x=>`<mark class="tok">${uhTok('CLIENT',x)}</mark>`).join(', ')}).</p>`:'';
  const legend=`<div class="uh-leg">${['removed','tokenized','generalized','redacted','allowed'].map(uhRule).join('')}</div>`;
  const re=t.conc.length?`<div class="uh-note warn"><b>Re-identification check:</b> ${t.conc.map(x=>esc(byId(x).name)).join(', ')} hold${t.conc.length===1?'s':''} a position above 20% of the household or insider stock. Figures like these can point to one person even without a name, so the request still goes only to an approved model deployment.</div>`:'';
  return legend+q+ctx+tbl+others+re}
function uhPrompt(t){return`<h4>Payload sent to the model</h4><pre class="uh-pre">${uhHi(t.pj)}</pre>
  <h4>The model’s answer, in tokens</h4><div class="uh-box">${uhHi(t.raw)}</div>
  <h4>Shown to you, names restored</h4><div class="uh-box">${esc(t.shown)}</div>
  <p class="small muted">The token table (${UH_TOK.m.size} entries this session) stays in the page: <button class="linkbtn small" data-uhtoks="1">${UH.toks?'hide':'show'} it</button>.</p>
  ${UH.toks?`<table class="uh-t"><thead><tr><th>Token</th><th>Stands for</th></tr></thead><tbody>${[...UH_TOK.m.entries()].slice(0,60).map(([k,v])=>`<tr><td><mark class="tok">${v}</mark></td><td>${esc(k.split(':').slice(1).join(':').replace(/^([a-z]+)$/,m=>byId(m)?.name||m))}</td></tr>`).join('')}</tbody></table>`:''}`}
function uhSvc(t){
  const rows=t.G.map(g=>{const a=UH_API[g.fn],hh=[...g.hh];
    return`<li><div class="uh-api"><span class="uh-m ${a[0]==='GET'?'get':'post'}">${a[0]}</span><code>${esc(a[1].replace('{a}',S.adv).replace('{h}',hh.length===1?hh[0]:'{household}').replace('{k}',String(g.args.find(x=>CK[x])||'{criterion}')))}</code></div>
      <div class="small"><b>${esc(a[2])}</b>${hh.length>1?` · ${hh.length} households in one batched request`:''}</div>
      <div class="uh-2"><div><div class="uh-l">The model asks</div><code class="small">${esc(g.fn)}(${uhHi(g.argv.filter(x=>x!=null).map(x=>x.h?uhTok('CLIENT',x.h.id):typeof x==='string'?uhRedact(x).t:String(x)).join(', '))})${hh.length>1?` <span class="muted">for ${hh.length} households</span>`:''}</code></div><div><div class="uh-l">The service receives</div><code class="small">${esc(g.argv.filter(x=>x!=null).map(x=>x.h?x.h.id:String(x)).join(', '))}</code></div></div>
      <details><summary class="small">Result sent to the model</summary><pre class="uh-pre">${uhHi(JSON.stringify(g.ret[0],null,1))}</pre></details></li>`}).join('');
  return`<h4>Services called</h4>${rows?`<ol class="uh-svc">${rows}</ol>`:'<p class="small muted">No service call: this answer comes from the screen’s context only.</p>'}
   <h4>Rules applied</h4>${t.rules.length?`<ul class="uh-ul">${[...new Map(t.rules.map(r=>[r.r,r])).values()].map(r=>`<li>${esc(r.r)} <span class="muted small">· ${esc(UH_API[r.fn][2])}</span></li>`).join('')}</ul>`:'<p class="small muted">No program rule involved.</p>'}
   <h4>Sources cited</h4>${t.srcs.length?`<ul class="uh-ul">${t.srcs.map(s=>`<li>${esc(s)}</li>`).join('')}</ul>`:'<p class="small muted">No document cited: the answer is figures from the services.</p>'}
   <p class="small muted">Paths are illustrative names for the services that would sit behind the screens. The gateway swaps tokens for internal IDs before calling them.</p>`}
function uhGuard(t){return`<ul class="uh-checks">${t.checks.map(c=>`<li class="${c.ok?'ok':'bad'}"><span class="uh-ck">${c.ok?'✓':'✕'}</span><div><b>${esc(c.name)}</b> <span class="uh-tag">${c.live?'ran on this answer':'policy'}</span><div class="small">${esc(c.detail)}</div></div></li>`).join('')}</ul>
  <div class="uh-note">Order in production: the app resolves names → the services return approved fields → the gateway scans free text and checks the payload → the model answers → the answer is scanned → names are restored on screen. Logs keep only the tokenized version.</div>`}
/* evals: two run live in this page; the rest are release gates */
const UH_DET=[
 ['Call Margaret Henderson at (555) 555-0142 about the gift',['Person name','Phone']],
 ['Her SSN is 912-34-5678, please update the file',['SSN or tax ID']],
 ['Send the proposal to owen.whitaker@example.com',['Email']],
 ['Move account 4X1-48213 into the CIO model',['Account number']],
 ['Paul was born 1958-04-12, check the RMD',['Person name','Date of birth']],
 ['They moved to 418 Linden Lane last spring',['Street address']],
 ['How risky is Kaplan right now?',['Client name']],
 ['What is the tax on the Lund Family transition at $250K?',['Client name']],
 ['Is a $500K budget too high for this client?',[]],
 ['Compare AAPL and MSFT exposure across the book',[]],
 ['Call Maggie about the trust before Friday',['Person name']],
 ['his social is nine one two three four five six seven eight',['SSN or tax ID']],
 ['Email from Jordan Blake (new prospect) about the referral',['Person name']],
];
function uhRunDet(){let tp=0,fn=0,fp=0;const miss=[],extra=[];
  for(const[s,exp]of UH_DET){const got=uhRedact(s).found.map(f=>f.type);const g=[...got];
    for(const e of exp){const i=g.indexOf(e);if(i>=0){tp++;g.splice(i,1)}else{fn++;miss.push([s,e])}}
    for(const x of g){fp++;extra.push([s,x])}}
  UH.det={n:UH_DET.length,tp,fn,fp,miss,extra}}
function uhRunSweep(){const t0=performance.now(),saved={book:{...S.book},chat:S.chat.length,ctx:ctxOf,lastCtx:S.lastCtx};let n=0,ids=0,leak=0,out=0,stray=0,left=0;const bad=[];
  const Q=['How risky is the portfolio?','What should I raise in the meeting?','What are the tax opportunities?','Why is the drift where it is?'];
  const QW=['Compare the options','What is the tax impact?','What is the risk shift?','What does it cost?','How long does the transition take?','What counts toward the budget?'];
  try{for(const h of HH()){
    ctxOf=()=>({kind:'client',h,lvl:'l1',f:null,show:'today',key:'sweep:'+h.id,line:'',plain:h.name});
    for(const q of Q.concat([`Tell me about ${h.name}`])){const{tr}=uhRun('panel',q,ctxOf(),()=>atlasAnswer(q));n++;ids+=tr.nIds;if(tr.leaks.length){leak++;bad.push([h.name,q,tr.leaks.join(', ')])}
      const c=tr.checks;if(!c[6].ok)out++;if(!c[7].ok)stray++;if(!c[8].ok)left++;delete UH.T[tr.id]}
    if(opps(h).some(o=>o.k==='advisory'))for(const q of QW){const{tr}=uhRun('wf',q,{kind:'wf',h,k:'advisory',plain:h.name},()=>wfAnswer(h,'advisory',q));n++;ids+=tr.nIds;if(tr.leaks.length){leak++;bad.push([h.name,q,tr.leaks.join(', ')])}
      const c=tr.checks;if(!c[6].ok)out++;if(!c[7].ok)stray++;if(!c[8].ok)left++;delete UH.T[tr.id]}}}
  finally{ctxOf=saved.ctx;S.book=saved.book;S.lastCtx=saved.lastCtx}
  UH.sweep={n,ids,leak,out,stray,left,bad,hh:HH().length,ms:Math.round(performance.now()-t0)}}
function uhEvals(t){const d=UH.det,s=UH.sweep;
  const row=(name,what,bar,res,live)=>`<tr><td><b>${name}</b><div class="small muted">${what}</div></td><td class="small">${bar}</td><td class="small">${res}</td></tr>`;
  const sweepRes=s?`<b class="${s.leak||s.out||s.stray||s.left?'neg':'pos'}">${s.leak?s.leak+' leaks':'No leaks'}</b> in ${s.n} answers over ${s.hh} households (${s.ids.toLocaleString()} identifier checks); answer scan ${s.out?s.out+' failed':'clean'}; tokens ${s.stray?s.stray+' unexpected':'all in scope'}; names restored ${s.left?s.left+' failed':'every time'}. ${s.ms} ms.${s.bad.length?`<ul>${s.bad.slice(0,4).map(b=>`<li>${esc(b[0])} · ${esc(b[1])}: ${esc(b[2])}</li>`).join('')}</ul>`:''}`:`<button class="btn sm primary" data-uheval="sweep">Run on ${esc(DATA.advisors[S.adv].split(' ')[0])}’s book</button>`;
  const detRes=d?`Caught <b>${d.tp} of ${d.tp+d.fn}</b> identifiers in ${d.n} messages; ${d.fp} false alarm${d.fp===1?'':'s'}. <b class="${d.fn?'neg':'pos'}">${d.fn?'Below the release bar':'Meets the bar'}</b>.${d.miss.length?`<ul>${d.miss.map(([s,e])=>`<li>Missed (${esc(e)}): “${esc(s)}”</li>`).join('')}</ul><span class="muted">Patterns and a name list miss nicknames, spelled-out numbers and people not in the book. Production adds a trained name recognizer, then reruns this set.</span>`:''}`:`<button class="btn sm primary" data-uheval="det">Run ${UH_DET.length} labeled messages</button>`;
  return`<p class="small">Two evals run here, in your browser, through the same gateway code as the answers. The others are release gates for production.</p>
  <table class="uh-t uh-ev"><thead><tr><th>Eval</th><th>Pass bar</th><th>Result</th></tr></thead><tbody>
   ${row('Leak test with planted identifiers','Every sample household carries made-up tax IDs, addresses, phones, emails and account numbers. Ask the standard questions for every household and check the payloads.','No planted value in any payload',sweepRes)}
   ${row('Free-text detector','Labeled advisor messages: names, phones, tax IDs, emails, account numbers, addresses, plus hard cases.','Catches every structured ID; few false alarms',detRes)}
   ${row('Answer scan and token scope','Every answer is scanned for identifiers, and every token must belong to its own request.','100%',`This answer: <b class="${t.checks[6].ok&&t.checks[7].ok?'pos':'neg'}">${t.checks[6].ok&&t.checks[7].ok?'passed':'failed'}</b>. Also part of the book test above.`)}
   ${row('Name restoration','No token left on screen; the right client’s name every time.','100%',`This answer: <b class="${t.checks[8].ok?'pos':'neg'}">${t.checks[8].ok?'passed':'failed'}</b>.`)}
   ${row('Attack tests','Instructions hidden in notes or documents, “list every client’s account number”, clients outside the book.','All refused or blocked','<span class="muted">Release gate; not run in the prototype</span>')}
   ${row('Accuracy with tokens','The same questions answered with and without tokens.','No drop in accuracy','<span class="muted">Release gate; needs the real model</span>')}
   ${row('Re-identification review','Sample real payloads; check whether the details point to one person.','Reviewer signs off',t.conc.length?`<span class="muted">Flagged for this answer: ${t.conc.length===1?'a household':t.conc.length+' households'} with a large single position or insider stock</span>`:'<span class="muted">Nothing flagged for this answer</span>')}
   ${row('Log and vendor audit','Gateway logs and the model provider’s retention settings.','No raw identifiers; retention off','<span class="muted">Release gate</span>')}
  </tbody></table>`}
function uhShow(id){UH.open=id;let p=document.getElementById('uhp');if(!p){p=document.createElement('aside');p.id='uhp';p.className='uhp';p.setAttribute('role','dialog');p.setAttribute('aria-label','Under the hood');document.body.appendChild(p)}
  p.innerHTML=uhPanel();p.hidden=false;document.body.classList.add('uh-open')}
function uhClose(){const p=document.getElementById('uhp');if(p)p.hidden=true;UH.open=null;document.body.classList.remove('uh-open')}
function uhToggle(){UH.on=!UH.on;try{localStorage.setItem('atlas-uh',UH.on?'1':'0')}catch(e){}uhPaintBtn();if(!UH.on)uhClose();rerenderKeep();
  toast(UH.on?'Under the hood is on: select a label on the screen, or the strip under any Atlas answer.':'Under the hood is off.')}
function uhPaintBtn(){const b=document.getElementById('uhbtn');if(b){b.setAttribute('aria-pressed',UH.on);b.classList.toggle('on',UH.on)}document.body.classList.toggle('uh-on',UH.on)}
document.querySelector('header.top .sp').insertAdjacentHTML('afterend',`<button class="uhbtn" id="uhbtn" data-uhtoggle="1" aria-pressed="false" title="Show what Atlas retrieves, what the model would see, and the guardrails"><span class="sw" aria-hidden="true"><span></span></span><span class="lbl">Under the hood</span></button>`);
document.addEventListener('click',e=>{
  if(e.target.closest('[data-uhtoggle]')){uhToggle();return}
  const s=e.target.closest('[data-uh]');if(s){e.preventDefault();e.stopPropagation();UH.tab=UH.tab||'flow';uhShow(s.dataset.uh);return}
  const tb=e.target.closest('[data-uhtab]');if(tb){UH.tab=tb.dataset.uhtab;uhShow(UH.open);document.querySelector('#uhp .uh-b')?.scrollTo(0,0);return}
  if(e.target.closest('[data-uhclose]')){uhClose();return}
  if(e.target.closest('[data-uhtoks]')){UH.toks=!UH.toks;uhShow(UH.open);return}
  const ev=e.target.closest('[data-uheval]');if(ev){ev.disabled=true;ev.textContent='Running…';setTimeout(()=>{if(ev.dataset.uheval==='sweep')uhRunSweep();else uhRunDet();uhShow(UH.open)},30);return}
  if(UH.open&&!e.target.closest('#uhp'))uhClose();
},true);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&UH.open){e.stopPropagation();uhClose()}},true);
uhPaintBtn();
