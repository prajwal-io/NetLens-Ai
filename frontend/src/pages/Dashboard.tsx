import { usePreference } from '../hooks/preferences';
import { TrafficChart } from '../components/TrafficChart';
import { NetworkMap } from '../components/NetworkMap';


import { Link } from 'react-router-dom';

import { Box, ArrowRight, CheckCircle2, FlaskConical } from 'lucide-react';


import { activity, totals } from '../fixtures/sample';

import type { Health } from '../services/api';

import { Panel, Sample } from '../components/ui';

import { FlowTable } from '../components/FlowTable';

const isRange=(v:unknown):v is string=>v==='3 hours'||v==='Last hour';
export default function Dashboard({health}:{health:Health|null}){

const [window,setWindow]=usePreference('chart-range','3 hours',isRange);

const chart=window==='Last hour'?activity.slice(-4):activity;

return <><div className="notice"><Box size={17}/><span><strong>An honest view of the foundation.</strong> Charts and flow records below use sample UI data, not live traffic or ML predictions.</span><Sample/></div>

<div className="metrics">{[['Total traffic flows',(totals.normal+totals.suspicious).toLocaleString(),'Full 3-hour sample'],['Normal traffic',totals.normal.toLocaleString(),'Sample normal classifications'],['Suspicious traffic',totals.suspicious.toLocaleString(),'Sample suspicious classifications'],['Model availability','Not loaded','Training begins in Phase 2']].map(([label,value,note])=><div key={label}><p>{label}</p><strong>{value}</strong><small>{note}</small></div>)}</div>

<Panel title="Workspace readiness" className="readiness-panel"><div className="readiness"><div><span className={health?'status-dot':'status-dot offline'}/><span><strong>FastAPI backend</strong><small>{health?'Connected to local API':'Waiting for connection'}</small></span></div><div><CheckCircle2 size={17}/><span><strong>CSV validation</strong><small>Schema and numeric checks ready</small></span></div><div><FlaskConical size={17}/><span><strong>ML pipeline</strong><small>No trained model installed</small></span></div></div><Link className="text-action" to="/traffic-analyzer">Validate your first dataset <ArrowRight size={15}/></Link></Panel><div className="dashboard-grid"><Panel title="Traffic activity" aside={<select aria-label="Chart time window" value={window} onChange={e=>setWindow(e.target.value)}><option>3 hours</option><option>Last hour</option></select>}><div className="chart-caption"><span>Flow volume over time</span><div><i className="dot blue"/>Normal <i className="dot red-dot"/>Suspicious</div></div><div className="chart"><TrafficChart data={chart}/></div><details className="chart-data"><summary>Read chart data</summary><table><caption>Sample traffic activity</caption><thead><tr><th scope="col">Time</th><th scope="col">Normal</th><th scope="col">Suspicious</th></tr></thead><tbody>{chart.map(r=><tr key={r.time}><th scope="row">{r.time}</th><td>{r.normal}</td><td>{r.suspicious}</td></tr>)}</tbody></table></details><div className="chart-foot">Sample snapshot | {chart[0].time}-{chart[chart.length-1].time} <span>No live packet capture</span></div></Panel>

<Panel title="Traffic distribution"><div className="distribution"><div className="traffic-ring"><svg className="ring-svg" viewBox="0 0 160 160" aria-hidden="true"><circle cx="80" cy="80" r="70" fill="none" stroke="var(--signal-red)" strokeWidth="10"/><circle cx="80" cy="80" r="70" fill="none" stroke="var(--signal-blue)" strokeWidth="10" pathLength="100" strokeDasharray={`${totals.normal/(totals.normal+totals.suspicious)*100} 100`} transform="rotate(-90 80 80)"/></svg><div><strong>{(totals.normal/(totals.normal+totals.suspicious)*100).toFixed(1)}%</strong><small>Normal traffic</small></div></div></div><div className="legend-row"><span><i className="dot blue"/>Normal</span><strong>{totals.normal.toLocaleString()}</strong></div><div className="legend-row"><span><i className="dot red-dot"/>Suspicious</span><strong>{totals.suspicious}</strong></div><p className="fine">Full 3-hour sample / illustrative labels, not model output.</p></Panel>

<Panel className="records-panel" title="Recent traffic records" aside={<Link to="/threat-investigation">Inspect samples <ArrowRight size={14}/></Link>}><FlowTable/></Panel>

<Panel title="Connection atlas" className="atlas-panel"><NetworkMap compact/></Panel></div>

</>}
