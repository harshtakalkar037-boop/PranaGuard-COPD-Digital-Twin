// Read-only accessibility smoke test against an explicitly disposable synthetic demo.
// Run with E2E_BASE, E2E_DOCTOR, E2E_DOCTOR_PASSWORD, E2E_PATIENT,
// E2E_PATIENT_PASSWORD and E2E_CHROMIUM_PATH set. Doctor needs the entire
// synthetic workspace assigned; patient must be linked. This is not a WCAG audit.
import {chromium} from 'playwright-core';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const axeSource=require.resolve('axe-core/axe.min.js');
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_DOCTOR_PASSWORD:doctorPassword,E2E_PATIENT:patient,E2E_PATIENT_PASSWORD:patientPassword,E2E_CHROMIUM_PATH:executablePath}=process.env;
if(!base||!doctor||!doctorPassword||!patient||!patientPassword||!executablePath)throw new Error('Explicit disposable synthetic demo and Chromium configuration required');
const patientId=process.env.E2E_PATIENT_ID||'PG-0001';
const widths=[390,768,1440];
const research=['overview','registry','patient','devices','environment','explain','scenario','validation','activity','notifications','sources','status'];
const care=['Care Action Centre','Sputum Monitoring','Patient Activity & Adherence','Care Plans','Add Patient','Notifications','Environment','Research tools'];
const patientViews=['Home','My Health','Symptom Check-in','Sputum Diary','My Daily Care Plan','Upload Documents','My Care Plan','Notifications','My Profile'];
const failures=[];
let scans=0;
const browser=await chromium.launch({executablePath,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage({viewport:{width:1440,height:900}});
async function go(path){
 await page.goto(base+path,{waitUntil:'networkidle'});
 await page.locator('.loading').first().waitFor({state:'hidden',timeout:30000});
 if(await page.locator('.error-banner,.portal-error').count())throw new Error(`Error displayed on ${path}`);
 await page.addScriptTag({path:axeSource});
}
async function scan(path){
 await go(path);
 for(const width of widths){
  await page.setViewportSize({width,height:900});
  // Let responsive chart/layout observers settle after the viewport changes.
  await page.waitForTimeout(250);
  const result=await page.evaluate(async()=>({violations:(await window.axe.run(document)).violations.map(v=>({id:v.id,impact:v.impact,count:v.nodes.length})),overflow:document.documentElement.scrollWidth>innerWidth+1}));
  scans++;
  for(const v of result.violations)failures.push(`${path} ${width}: ${v.id} ${v.impact} (${v.count})`);
  if(result.overflow)failures.push(`${path} ${width}: document overflows viewport`);
 }
}
async function login(role,user,password){
 await page.goto(base+`/${role}/login`);
 await page.getByLabel('Username').fill(user);
 await page.getByLabel('Password',{exact:true}).fill(password);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.waitForURL(`**/${role}/dashboard`);
}
try{
 for(const path of ['/','/doctor/login','/patient/login'])await scan(path);
 // Keyboard form focus order, visible focus, and announced server-side error.
 await page.goto(base+'/doctor/login');await page.keyboard.press('Tab');await page.keyboard.press('Tab');
 const username=page.getByLabel('Username');await username.focus();
 if(!await username.evaluate(el=>document.activeElement===el && getComputedStyle(el).outlineStyle!=='none'))throw new Error('Login field lacks visible focus');
 await username.fill('missing-user');await page.keyboard.press('Tab');
 if(!await page.getByLabel('Password',{exact:true}).evaluate(el=>document.activeElement===el))throw new Error('Login focus order does not move from username to password');
 await page.getByLabel('Password',{exact:true}).fill('incorrect');await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByRole('alert').getByText('Invalid credentials').waitFor();
 await login('doctor',doctor,doctorPassword);
 for(const view of research)await scan(`/doctor/dashboard?patient=${encodeURIComponent(patientId)}#${view}`);
 for(const view of care)await scan(`/doctor/dashboard?patient=${encodeURIComponent(patientId)}#care:${encodeURIComponent(view)}`);
 // Exercise keyboard activation of the patient row action, rather than relying on click-only rows.
 await page.goto(base+'/doctor/dashboard#overview',{waitUntil:'networkidle'});
 await page.getByLabel('Search patients').fill(patientId);
 const open=page.getByRole('button',{name:`Open ${patientId}`,exact:true});
 await open.focus();
 if(!await open.evaluate(el=>document.activeElement===el))throw new Error('Patient action cannot receive keyboard focus');
 await page.keyboard.press('Enter');
 await page.getByRole('heading',{name:'Patient digital twin',level:1}).waitFor();
 // Narrow-screen navigation is keyboard reachable, labelled and closes on Escape.
 await page.setViewportSize({width:390,height:844});await page.emulateMedia({reducedMotion:'reduce'});
 const menu=page.getByRole('button',{name:'Open navigation'});await menu.focus();await page.keyboard.press('Enter');
 const closeMenu=page.getByRole('button',{name:'Close navigation'});
 if(await closeMenu.getAttribute('aria-expanded')!=='true')throw new Error('Navigation expanded state missing');
 if(!await page.getByRole('button',{name:'Cohort overview',exact:true}).evaluate(el=>document.activeElement===el))throw new Error('Opened navigation did not receive focus');
 const motion=await page.locator('#research-navigation').evaluate(el=>getComputedStyle(el).transitionDuration);
 if(motion.split(',').some(value=>parseFloat(value)>0.001))throw new Error('Reduced motion preference not respected');
 await page.keyboard.press('Escape');
 if(await page.getByRole('button',{name:'Open navigation'}).getAttribute('aria-expanded')!=='false')throw new Error('Escape did not close navigation');
 if(!await page.getByRole('button',{name:'Open navigation'}).evaluate(el=>document.activeElement===el))throw new Error('Navigation did not restore focus');
 if(await page.locator('#research-navigation').evaluate(el=>getComputedStyle(el).visibility)!=='hidden')throw new Error('Closed navigation remains keyboard accessible');
 await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1440,height:900});
 // The calibration chart has an accessible data alternative, with values from the API.
 await page.goto(base+'/doctor/dashboard#validation',{waitUntil:'networkidle'});
 const data=await page.evaluate(async()=>{const token=sessionStorage.getItem('pg-portal-token');const response=await fetch('/api/validation',{headers:{Authorization:`Bearer ${token}`}});if(!response.ok)throw new Error('Validation request failed');return response.json()});
 const summary=page.getByText('Show Calibration plot values (four decimals)',{exact:true});
 await summary.focus();await page.keyboard.press('Enter');
 const first=data.diagnostics['72'].calibration[0];
 if(first){const table=page.getByRole('region',{name:'Calibration plot values'});await table.getByText(first.predicted.toFixed(4),{exact:true}).first().waitFor();await table.getByText(first.observed.toFixed(4),{exact:true}).first().waitFor();}
 await page.evaluate(()=>sessionStorage.removeItem('pg-portal-token'));
 await login('patient',patient,patientPassword);
 for(const view of patientViews)await scan(`/patient/dashboard?view=${encodeURIComponent(view)}`);
 if(failures.length){console.error(failures.join('\n'));throw new Error(`${failures.length} automated accessibility/overflow findings`)}
 console.log(`PASS: ${scans} axe/overflow scans plus login focus/error, mobile navigation, reduced motion, patient action and calibration data checks. Manual assistive-technology review remains necessary.`);
}finally{await browser.close()}
