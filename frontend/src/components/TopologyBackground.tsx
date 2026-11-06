import { useReducedMotion } from 'motion/react';
import { isBoolean, usePageVisibility, usePreference } from '../hooks/preferences';
/** Sparse edge topology uses the same paths and nodes as the interactive atlas.
 * It is presentational, never a representation of captured traffic. */
export function TopologyBackground(){
 const [paused]=usePreference('background-paused',false,isBoolean);
 const visible=usePageVisibility();const reduce=useReducedMotion();
 return <div className="topology-background" data-running={!paused&&visible&&!reduce} aria-hidden="true">
  <svg className="topology-edge topology-left" viewBox="0 0 320 900" fill="none">
   <defs><linearGradient id="edge-fade" x1="0" y1="0" x2="320" y2="0" gradientUnits="userSpaceOnUse"><stop stopColor="white" stopOpacity=".75"/><stop offset=".28" stopColor="white" stopOpacity=".15"/><stop offset="1" stopColor="white" stopOpacity="0"/></linearGradient><mask id="topology-mask"><rect width="320" height="900" fill="url(#edge-fade)"/></mask><pattern id="technical-grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" stroke="#3268f5" strokeOpacity=".11" strokeWidth=".6"/></pattern></defs>
   <g mask="url(#topology-mask)"><rect y="90" width="320" height="470" fill="url(#technical-grid)"/>
    <g stroke="#3268f5" strokeWidth=".8" strokeOpacity=".35">
     <path d="M-20 140H45Q70 140 70 165V212Q70 236 94 236H154Q178 236 178 260V338H304"/>
     <path d="M-20 310H32Q56 310 56 334V400Q56 424 80 424H126Q150 424 150 448V490H290"/>
     <path d="M-20 650H42Q66 650 66 626V590Q66 566 90 566H164Q188 566 188 542V516H310"/>
     <path d="M-10 810H22Q46 810 46 786V744Q46 720 70 720H138Q162 720 162 696V670H290"/>
     <path d="M70 190H112Q136 190 136 166V106H290M56 370H110Q134 370 134 346V312"/>
    </g>
    {[[45,140],[70,212],[154,236],[178,338],[32,310],[56,400],[126,424],[150,490],[42,650],[90,566],[188,542],[46,786],[138,720],[136,166]].map(([x,y])=><g key={x+'-'+y}><circle cx={x} cy={y} r="3" fill="#faf9f6" stroke="#3268f5" strokeOpacity=".5"/><circle cx={x} cy={y} r="1" fill="#3268f5" fillOpacity=".6"/></g>)}
    <path className="edge-signal" d="M-20 140H45Q70 140 70 165V212Q70 236 94 236H154Q178 236 178 260V338H304" stroke="#3268f5" strokeWidth="1.2" pathLength="100"/>
   </g>
  </svg>
  <svg className="topology-edge topology-right" viewBox="0 0 320 900" fill="none">
   <g transform="translate(320 900) rotate(180)" mask="url(#topology-mask)"><rect y="170" width="280" height="460" fill="url(#technical-grid)"/><g stroke="#3268f5" strokeWidth=".8" strokeOpacity=".35"><path d="M-10 180H46Q70 180 70 204V250Q70 274 94 274H160Q184 274 184 298V350H305"/><path d="M-20 460H38Q62 460 62 436V402Q62 378 86 378H136Q160 378 160 354V330H300"/><path d="M-20 740H50Q74 740 74 716V652Q74 628 98 628H172Q196 628 196 604V566H312"/><path d="M70 222H118Q142 222 142 198V120H280"/></g>{[[46,180],[70,250],[160,274],[184,350],[38,460],[86,378],[160,354],[50,740],[74,652],[172,628],[196,566],[142,198]].map(([x,y])=><circle key={x+'-'+y} cx={x} cy={y} r="3" fill="#faf9f6" stroke="#3268f5" strokeOpacity=".5"/>)}<path className="edge-signal edge-signal-delayed" d="M-20 740H50Q74 740 74 716V652Q74 628 98 628H172Q196 628 196 604V566H312" stroke="#3268f5" strokeWidth="1.2" pathLength="100"/></g>
  </svg>
 </div>
}
