import { AnalysisHistory } from './components/AnalysisHistory';
import { ErrorBoundary, PageSkeleton, PageNotFound } from './components/Recovery';
import { useBackendStatus } from './hooks/backend';
import { isBoolean, usePreference } from './hooks/preferences';
import { TopologyBackground } from './components/TopologyBackground';
import { lazy, Suspense, useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, NavLink, Route, Routes, Link, useLocation } from 'react-router-dom';
import { Activity, FileBarChart2, FlaskConical, LayoutDashboard, Network, RefreshCw, ShieldCheck, ArrowUpRight, Menu, ChevronDown, Pause, Play } from 'lucide-react';
import { m, LazyMotion, domAnimation, MotionConfig, useReducedMotion } from 'motion/react';
const Analyzer = lazy(()=>import('./pages/Analyzer'));
const Investigation = lazy(()=>import('./pages/Investigation'));
const Pulse = lazy(()=>import('./pages/Pulse'));
const ModelLab = lazy(()=>import('./pages/ModelLab'));
const Reports = lazy(()=>import('./pages/Reports'));
const Dashboard = lazy(()=>import('./pages/Dashboard'));
const Landing = lazy(()=>import('./pages/Landing'));


import '@fontsource/inter/latin-400.css';
import '@fontsource/inter/latin-500.css';
import '@fontsource/inter/latin-600.css';
import '@fontsource/space-grotesk/latin-500.css';
import './style.css';
import './editorial.css';
import './quality.css';
import './completion.css';
import './theme.css';
import './analyst-command.css';
import './background-motion.css';
import './release.css';
import './dashboard-console.css';

const pages = [
 {path:'/command-center',name:'Command Center',icon:LayoutDashboard,primary:true},
 {path:'/network-pulse',name:'Network Pulse',icon:Network,primary:true},
 {path:'/traffic-analyzer',name:'Traffic Analyzer',icon:Activity,primary:true},
 {path:'/threat-investigation',name:'Threat Investigation',icon:ShieldCheck,primary:true},
 {path:'/reports',name:'Reports',icon:FileBarChart2,primary:true},
 {path:'/model-lab',name:'Model Lab',icon:FlaskConical,primary:false}
];
const navigation = pages.filter(page=>page.primary);
function ProductHeader({landing}:{landing:boolean}){
 const menu=useRef<HTMLDetailsElement>(null);
 const [paused,setPaused]=usePreference('background-paused',false,isBoolean);
 const reduce=useReducedMotion();
 const location=useLocation();
 useEffect(()=>{menu.current?.removeAttribute('open')},[location]);
 const current=pages.find(n=>n.path===location.pathname)?.name??'Explore NetSight';
 const siteLinks=[['#the-problem','The problem'],['#the-approach','Our approach'],['#how-it-works','How it works'],['#capabilities','Capabilities']];

 return <header className={'product-header '+(landing?'on-landing':'')}><div className="product-header-inner"><Link to="/" className="brand" aria-label="NetSight AI home"><img src="/netsight-ai-logo.png" alt="NetSight AI" className="brand-logo" width="190" height="53" decoding="async"/></Link><span className="product-descriptor">Network intelligence, made clear.</span><div className="header-actions"><button className="background-motion-control" aria-label={reduce?'Background motion disabled by reduced-motion preference':paused?'Resume background animation':'Pause background animation'} title={reduce?'Reduced motion enabled':paused?'Resume background animation':'Pause background animation'} aria-pressed={paused} disabled={!!reduce} onClick={()=>setPaused(!paused)}>{paused||reduce?<Play size={15}/>:<Pause size={15}/>}</button><Link className="header-destination" to={landing?'/command-center':'/'}>{landing?'Open workspace':'The NetSight story'}<ArrowUpRight size={15}/></Link></div></div><nav className="floating-nav desktop-navigation" aria-label={landing?'Site navigation':'Workspace navigation'}>{landing?<><a href="#the-problem">The problem</a><a href="#the-approach">Our approach</a><a href="#how-it-works">How it works</a><a href="#capabilities">Capabilities</a><Link to="/command-center">Command Center <ArrowUpRight size={14}/></Link></>:navigation.map(n=><NavLink key={n.path} to={n.path}>{({isActive})=><>{isActive&&<m.span className="nav-active-surface" layoutId="workspace-nav-indicator" transition={{duration:0.2,ease:[0.23,1,0.32,1]}}/>}<n.icon size={15}/><span className="nav-link-label">{n.name}</span></>}</NavLink>)}</nav><details ref={menu} className="mobile-navigation" onKeyDown={e=>{if(e.key==='Escape'){menu.current?.removeAttribute('open');menu.current?.querySelector('summary')?.focus()}}}><summary><Menu size={18}/><span>{current}</span><ChevronDown size={17}/></summary><nav aria-label={landing?'Mobile site navigation':'Mobile workspace navigation'}>{landing?<>{siteLinks.map(([href,name])=><a key={href} href={href} onClick={()=>menu.current?.removeAttribute('open')}>{name}<ArrowUpRight size={15}/></a>)}<Link to="/command-center">Command Center<ArrowUpRight size={15}/></Link></>:navigation.map(n=><NavLink key={n.path} to={n.path} onClick={()=>menu.current?.removeAttribute('open')}><n.icon size={17}/>{n.name}<ArrowUpRight size={14}/></NavLink>)}</nav></details></header>;
}
function Workspace(){
 const {health,error,loading,lastChecked,lastGood,online,refresh}=useBackendStatus();
 const location=useLocation();const page=pages.find(n=>n.path===location.pathname);
 useEffect(()=>{document.title='NetSight AI | '+(page?.name??'Page not found')},[page?.name]);
 return <main id="main-content" tabIndex={-1} className="workspace-main"><div className="workspace-context"><nav className="breadcrumbs" aria-label="Breadcrumb"><Link to="/">NetSight</Link><span>/</span><Link to="/command-center">Workspace</Link><span>/</span><span aria-current="page">{page?.name??'Unknown page'}</span></nav><div className="connection" role="status" title={lastChecked?'Last checked '+lastChecked.toLocaleTimeString():'Waiting for first health check'}><span className={health?'status-dot':'status-dot offline'}/><span className="connection-label">{!online?'Offline':loading&&!lastChecked?'Checking API...':health?'Backend connected':'Backend offline'}</span><button aria-label="Refresh backend status" disabled={loading} onClick={refresh}><RefreshCw size={14} className={loading?'spin':''}/></button>{lastChecked&&<small className="last-checked">Checked {lastChecked.toLocaleTimeString()}</small>}</div></div><div className="page-heading"><div><h1>{page?.name??'Page not found'}</h1><p>{page?.path==='/command-center'?'Traffic and model results at a glance.':page?.path==='/traffic-analyzer'?'Check your data, then analyze its flows.':page?.path==='/threat-investigation'?'Review suspicious flows and their evidence.':page?.path==='/network-pulse'?'Replay historical traffic and explore its flows.':page?.path==='/model-lab'?'See how the model was trained and tested.':'Review and export saved analysis results.'}</p></div></div>{error&&<div className="error" role="status"><span>{error}{lastGood&&<small>Last successful connection: {lastGood.toLocaleTimeString()}</small>}</span><button disabled={loading} onClick={refresh}>Retry connection</button></div>}<AnalysisHistory/><Routes><Route path="/command-center" element={<Suspense fallback={<div className="page-skeleton" role="status" aria-busy="true">Loading traffic workspace...<span/><span/></div>}><Dashboard health={health}/></Suspense>}/><Route path="/network-pulse" element={<Pulse/>}/><Route path="/traffic-analyzer" element={<Analyzer health={health}/>} /><Route path="/threat-investigation" element={<Investigation/>}/><Route path="/model-lab" element={<ModelLab/>}/><Route path="/reports" element={<Reports/>}/><Route path="*" element={<PageNotFound/>}/></Routes><footer>NetSight AI <span>Local UNSW-NB15 flow analysis / evaluated model pipeline</span></footer></main>;
}
function App(){
 const {pathname}=useLocation();const landing=pathname==='/';
 useEffect(()=>{window.scrollTo(0,0)},[pathname]);
 return <LazyMotion features={domAnimation} strict><MotionConfig reducedMotion="user"><TopologyBackground/><a className="skip-link" href="#main-content">Skip to content</a><ProductHeader landing={landing}/><ErrorBoundary resetKey={pathname}><Suspense fallback={<PageSkeleton/>}>{landing?<main id="main-content" tabIndex={-1} className="landing-main"><Landing/></main>:<Workspace/>}</Suspense></ErrorBoundary></MotionConfig></LazyMotion>
}
createRoot(document.getElementById('root')!).render(<BrowserRouter><App/></BrowserRouter>);
