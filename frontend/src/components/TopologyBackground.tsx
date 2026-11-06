import type { CSSProperties } from 'react';
import { useReducedMotion } from 'motion/react';
import { isBoolean, usePageVisibility, usePreference } from '../hooks/preferences';

type Stream = {
  side: 'left' | 'right';
  offset: string;
  tone: 'blue' | 'red';
  duration: string;
  delay: string;
  tokens: string[];
};

// Sparse packet-like values keep the background tied to network telemetry.
// They are decorative marks, not live network data.
const streams: Stream[] = [
  { side: 'left', offset: '2%', tone: 'blue', duration: '31s', delay: '-18s', tokens: ['01', '4F', 'A2', '7C', '·', '02', 'B1', '30'] },
  { side: 'left', offset: '6%', tone: 'red', duration: '36s', delay: '-7s', tokens: ['ACK', '10', '·', 'F3', '21', '0A', '·', '02'] },
  { side: 'left', offset: '11%', tone: 'blue', duration: '34s', delay: '-28s', tokens: ['08', '2D', '90', '·', 'C4', '01', '1E', '72'] },
  { side: 'left', offset: '16%', tone: 'blue', duration: '39s', delay: '-12s', tokens: ['7F', '03', 'B8', '11', '·', 'A0', '24', '09'] },
  { side: 'right', offset: '2%', tone: 'blue', duration: '35s', delay: '-25s', tokens: ['3E', '04', '·', 'C1', '0D', '8A', '21', '·'] },
  { side: 'right', offset: '6%', tone: 'red', duration: '32s', delay: '-4s', tokens: ['SYN', '0A', '31', '·', '92', 'F0', '12', '03'] },
  { side: 'right', offset: '11%', tone: 'blue', duration: '38s', delay: '-20s', tokens: ['04', 'B2', '17', '·', 'A8', '02', '60', '1C'] },
  { side: 'right', offset: '16%', tone: 'blue', duration: '33s', delay: '-10s', tokens: ['2B', '·', '01', 'E7', '44', '09', '·', '30'] },
];

/** Decorative network topology and telemetry marks. It does not represent live traffic. */
export function TopologyBackground() {
  const [paused] = usePreference('background-paused', false, isBoolean);
  const visible = usePageVisibility();
  const reduce = useReducedMotion();
  const running = !paused && visible && !reduce;

  return (
    <div className="topology-background" data-running={running} aria-hidden="true">
      <svg className="topology-edge topology-left" viewBox="0 0 320 900" fill="none">
        <defs>
          <linearGradient id="edge-fade" x1="0" y1="0" x2="320" y2="0" gradientUnits="userSpaceOnUse">
            <stop stopColor="white" stopOpacity=".72" />
            <stop offset=".28" stopColor="white" stopOpacity=".14" />
            <stop offset="1" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <mask id="topology-mask"><rect width="320" height="900" fill="url(#edge-fade)" /></mask>
          <pattern id="technical-grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M48 0H0V48" stroke="var(--signal-blue)" strokeOpacity=".18" strokeWidth=".6" />
          </pattern>
        </defs>
        <g mask="url(#topology-mask)">
          <rect y="90" width="320" height="470" fill="url(#technical-grid)" />
          <g stroke="var(--signal-blue)" strokeWidth=".8" strokeOpacity=".56">
            <path d="M-20 140H45Q70 140 70 165V212Q70 236 94 236H154Q178 236 178 260V338H304" />
            <path d="M-20 310H32Q56 310 56 334V400Q56 424 80 424H126Q150 424 150 448V490H290" />
            <path d="M-20 650H42Q66 650 66 626V590Q66 566 90 566H164Q188 566 188 542V516H310" />
            <path d="M-10 810H22Q46 810 46 786V744Q46 720 70 720H138Q162 720 162 696V670H290" />
            <path d="M70 190H112Q136 190 136 166V106H290M56 370H110Q134 370 134 346V312" />
          </g>
          <path d="M-10 530H52Q76 530 76 506V470H126" stroke="var(--signal-red)" strokeWidth="1" strokeOpacity=".52" />
          {[[45, 140], [70, 212], [154, 236], [178, 338], [32, 310], [56, 400], [126, 424], [150, 490], [42, 650], [90, 566], [188, 542], [46, 786], [138, 720], [136, 166]].map(([x, y]) => (
            <g key={`${x}-${y}`}><circle cx={x} cy={y} r="3.5" fill="var(--paper)" stroke="var(--signal-blue)" strokeOpacity=".92" /><circle cx={x} cy={y} r="1" fill="var(--signal-blue)" fillOpacity=".9" /></g>
          ))}
          <path className="edge-signal" d="M-20 140H45Q70 140 70 165V212Q70 236 94 236H154Q178 236 178 260V338H304" stroke="var(--signal-blue)" strokeWidth="1.6" pathLength="100" />
        </g>
      </svg>

      <svg className="topology-edge topology-right" viewBox="0 0 320 900" fill="none">
        <g transform="translate(320 900) rotate(180)" mask="url(#topology-mask)">
          <rect y="170" width="280" height="460" fill="url(#technical-grid)" />
          <g stroke="var(--signal-blue)" strokeWidth=".8" strokeOpacity=".56">
            <path d="M-10 180H46Q70 180 70 204V250Q70 274 94 274H160Q184 274 184 298V350H305" />
            <path d="M-20 460H38Q62 460 62 436V402Q62 378 86 378H136Q160 378 160 354V330H300" />
            <path d="M-20 740H50Q74 740 74 716V652Q74 628 98 628H172Q196 628 196 604V566H312" />
            <path d="M70 222H118Q142 222 142 198V120H280" />
          </g>
          <path d="M-10 590H60Q84 590 84 566V528H138" stroke="var(--signal-red)" strokeWidth="1" strokeOpacity=".52" />
          {[[46, 180], [70, 250], [160, 274], [184, 350], [38, 460], [86, 378], [160, 354], [50, 740], [74, 652], [172, 628], [196, 566], [142, 198]].map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="3.5" fill="var(--paper)" stroke="var(--signal-blue)" strokeOpacity=".92" />
          ))}
          <path className="edge-signal edge-signal-delayed" d="M-20 740H50Q74 740 74 716V652Q74 628 98 628H172Q196 628 196 604V566H312" stroke="var(--signal-blue)" strokeWidth="1.6" pathLength="100" />
        </g>
      </svg>

      <div className="telemetry-rain">
        {streams.map((stream, index) => (
          <div
            className={`rain-column rain-column--${stream.tone} rain-column--${stream.side}`}
            key={`${stream.side}-${stream.offset}`}
            style={{
              [stream.side]: stream.offset,
              '--rain-duration': stream.duration,
              '--rain-delay': stream.delay,
            } as CSSProperties}
          >
            {stream.tokens.map((token, tokenIndex) => <span key={`${index}-${tokenIndex}`}>{token}</span>)}
          </div>
        ))}
      </div>
    </div>
  );
}
