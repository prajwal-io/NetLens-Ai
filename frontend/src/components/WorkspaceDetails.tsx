import { Link } from 'react-router-dom';
import { ArrowRight, Info } from 'lucide-react';
import type { ReactNode } from 'react';
export function ContextNote({children}:{children:ReactNode}){
 return <div className="context-note"><Info size={17} aria-hidden="true"/><p>{children}</p></div>
}
export function NextStep({title,description,to,label}:{title:string;description:string;to:string;label:string}){
 return <div className="next-step"><div><h3>{title}</h3><p>{description}</p></div><Link className="quiet-link" to={to}>{label}<ArrowRight size={17}/></Link></div>
}
export function DefinitionList({items}:{items:[string,string][]}){
 return <dl className="definition-list">{items.map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
}
