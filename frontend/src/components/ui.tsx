import type { ReactNode } from 'react';
export function Panel({title,aside,children,className=''}:{title:string;aside?:ReactNode;children:ReactNode;className?:string}) {return <section className={'panel '+className}><div className="panel-head"><h2>{title}</h2>{aside}</div>{children}</section>}
export function Empty({title,children}:{title:string;children:ReactNode}){return <div className="empty"><h3>{title}</h3><p>{children}</p></div>}
export function Sample(){return <span className="sample">Sample UI data</span>}
