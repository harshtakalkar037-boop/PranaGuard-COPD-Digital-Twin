// Mutates an explicitly configured local disposable fixture with record #1 beyond each history cap.
import {chromium} from 'playwright-core';
import {createRequire} from 'node:module';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:exe,E2E_DISPOSABLE:disposable}=process.env;
if(!base||!doctor||!password||!exe||disposable!=='1'||new URL(base).hostname!=='127.0.0.1')throw Error('Explicit local disposable fixture configuration required');
const pid=process.env.E2E_PATIENT_ID||'PG-0001';
const browser=await chromium.launch({executablePath:exe,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage({viewport:{width:1440,height:900}});page.setDefaultTimeout(30000);
const check=(condition,message)=>{if(!condition)throw Error(message)};
try {
 await page.goto(base+'/doctor/login');await page.getByLabel('Username').fill(doctor);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();
 const token=await page.evaluate(()=>sessionStorage.getItem('pg-portal-token'));const headers={Authorization:`Bearer ${token}`};
 const patient=await (await page.request.get(`${base}/api/portal/patients/${pid}`,{headers})).json();
 for(const key of ['checkins','uploads','reviews'])check(!patient[key].some(x=>x.id===1),`${key} fixture is not beyond its history cap`);
 const sputum=await (await page.request.get(`${base}/api/portal/patients/${pid}/sputum`,{headers})).json();check(!sputum.entries.some(x=>x.id===1),'Sputum fixture is not beyond its cap');
 const daily=await (await page.request.get(`${base}/api/portal/patients/${pid}/daily-care`,{headers})).json();check(!daily.logs.some(x=>x.id===1),'Daily fixture is not beyond its cap');
 await page.getByRole('button',{name:'Care Action Centre',exact:true}).click();const queue=page.locator('section.portal-card').filter({has:page.getByRole('heading',{name:'Review queue',exact:true})});await queue.getByLabel('Queue order').selectOption('oldest');
 const focused=page.locator('section.portal-card').filter({has:page.getByRole('heading',{name:'Selected queue record',exact:true})});
 async function select(kind,expected){await queue.getByLabel('Queue item type').selectOption(kind);const row=queue.locator('button').filter({has:page.locator('small').filter({hasText:/record #1$/})});await row.waitFor();await row.click();await focused.getByText(expected,{exact:true}).waitFor();check(await focused.getByRole('heading',{name:'Selected queue record'}).evaluate(e=>document.activeElement===e),'Selected record heading did not receive focus');}
 await select('checkin','Unique old checkin 0');await focused.getByText('Unique old followup 0').waitFor();
 await focused.getByText('Review this record').click();await focused.locator('select[name=status]').selectOption('Reviewed');await focused.getByLabel('Review notes').fill('Browser old checkin review');await focused.getByRole('button',{name:'Save review'}).click();await focused.getByText('Review saved for this record.').waitFor();
 let current=await (await page.request.get(`${base}/api/portal/patients/${pid}/queue-items/checkin/1`,{headers})).json();check(current.record.review_status==='Reviewed'&&current.record.reviews[0].notes==='Browser old checkin review','Wrong checkin reviewed');
 await select('upload','Unique old upload 0');await focused.getByText('Unique old followup 0').waitFor();const downloadPromise=page.waitForEvent('download');await focused.getByRole('button',{name:'Download securely'}).click();const download=await downloadPromise;check(download.suggestedFilename()==='plan0.pdf','Wrong upload downloaded');
 await focused.getByText('Review this record').click();await focused.locator('select[name=status]').selectOption('Reviewed');await focused.getByLabel('Review notes').fill('Browser old upload review');await focused.getByRole('button',{name:'Save review'}).click();await focused.getByText('Review saved for this record.').waitFor();
 await select('sputum','Unique old sputum 0');await focused.getByText('Review this entry').click();await focused.getByLabel('Review notes').fill('Browser old sputum review');await focused.getByRole('button',{name:'Mark reviewed and save'}).click();await focused.getByText('Review saved.').waitFor();
 await select('daily','Unique old daily 0');await focused.getByText('Review activity').click();await focused.getByLabel('Review note',{exact:true}).fill('Browser old daily review');await focused.getByRole('button',{name:'Mark reviewed'}).click();await focused.getByText(/Doctor review: Browser old daily review/).waitFor();
 await select('followup','Unique old followup 0');await focused.getByText('Unique old checkin 0').waitFor();await focused.getByText('Unique old upload 0').waitFor();await focused.getByText('Complete dated follow-up').click();await focused.getByLabel('Completion note').fill('Browser old follow-up completed');await focused.getByRole('button',{name:'Record follow-up completion'}).click();await focused.getByText(/Follow-up completion recorded/).waitFor();
 for(const [kind,field,text] of [['upload','review_status','Reviewed'],['sputum','review_status','Reviewed'],['daily','review_status','Reviewed'],['followup','followup_completion_notes','Browser old follow-up completed']]){const r=await page.request.get(`${base}/api/portal/patients/${pid}/queue-items/${kind}/1`,{headers});check(r.ok()&&(await r.json()).record[field]===text,`${kind} update failed`);}
 await page.addScriptTag({path:createRequire(import.meta.url).resolve('axe-core/axe.min.js')});
 for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});const result=await page.evaluate(async()=>({violations:(await window.axe.run(document)).violations.map(v=>`${v.id}: ${v.nodes.map(n=>`${n.target.join(' ')} ${n.failureSummary}`).join('; ')}`),overflow:document.documentElement.scrollWidth>innerWidth+1}));check(!result.violations.length&&!result.overflow,`Width ${width}: ${JSON.stringify(result)}`);}
 console.log('PASS: exact old queue record, linked reviews, upload download, all five review/completion actions, and three axe/overflow scans');
} finally {await browser.close()}
