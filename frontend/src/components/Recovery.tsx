import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

export class ErrorBoundary extends Component<{children:ReactNode;resetKey:string},{failed:boolean}>{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true}}
 componentDidCatch(error:Error,info:ErrorInfo){console.error('NetSight interface failure',error,info.componentStack)}
 componentDidUpdate(previous:{resetKey:string}){if(previous.resetKey!==this.props.resetKey&&this.state.failed)this.setState({failed:false})}
 render(){
  if(!this.state.failed)return this.props.children;
  return <main id="main-content" tabIndex={-1} className="workspace-main"><section className="recovery-panel" role="alert"><h1>This view could not load.</h1><p>Your uploaded file has not been saved. You can try the view again or return to Command Center.</p><div className="recovery-actions"><button className="primary" onClick={()=>this.setState({failed:false})}>Try this view again</button><button onClick={()=>location.reload()}>Reload application</button><Link to="/command-center">Return to Command Center</Link></div></section></main>;
 }
}
export function PageSkeleton(){
 return <main id="main-content" tabIndex={-1} className="workspace-main" aria-busy="true"><p role="status" className="loading-label">Loading workspace...</p><div className="page-skeleton" aria-hidden="true"><span/><span/><div><span/><span/></div></div></main>;
}
export function PageNotFound(){
 return <section className="recovery-panel"><p className="fine">404 / Unknown destination</p><h2>There is no page here.</h2><p>Choose a workspace destination or return to the NetSight story.</p><div className="recovery-actions"><Link className="primary" to="/command-center">Open Command Center</Link><Link to="/">Read the NetSight story</Link></div></section>;
}
