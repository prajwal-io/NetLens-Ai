import { useEffect, useMemo, useState } from 'react';
import type { Analysis } from '../services/api';

export function FlowExperience({ analysis }: { analysis: Analysis }) {
  const replay = analysis.source_type === 'historical_replay';
  const [position, setPosition] = useState(replay ? 0 : analysis.total_flows);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [selected, setSelected] = useState('');
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => setPosition(value => Math.min(analysis.total_flows, value + 1)), 500 / speed);
    return () => window.clearInterval(timer);
  }, [playing, speed, analysis.total_flows]);
  useEffect(() => { if (position >= analysis.total_flows) setPlaying(false); }, [position, analysis.total_flows]);
  const visible = useMemo(() => analysis.predictions.slice(0, position), [analysis.predictions, position]);
  const network = useMemo(() => {
    const edges = new Map<string, { source: string; destination: string; count: number; malicious: number }>();
    const nodes = new Set<string>();
    for (const row of visible) {
      if (!row.source || !row.destination) continue;
      const key = `${row.source}>${row.destination}`;
      if (!edges.has(key) && (edges.size >= 80 || (!nodes.has(row.source) && nodes.size >= 39) || (!nodes.has(row.destination) && nodes.size >= 39))) continue;
      nodes.add(row.source); nodes.add(row.destination);
      const edge = edges.get(key) ?? { source: row.source, destination: row.destination, count: 0, malicious: 0 };
      edge.count++; edge.malicious += row.label === 'malicious' ? 1 : 0; edges.set(key, edge);
    }
    const points = [...nodes].map((id, index, all) => ({ id, x: 450 + 335 * Math.cos(index / all.length * Math.PI * 2), y: 240 + 175 * Math.sin(index / all.length * Math.PI * 2) }));
    return { edges: [...edges.values()], points };
  }, [visible]);
  const malicious = visible.filter(row => row.label === 'malicious').length;
  const hasTopology = analysis.predictions.some(row => row.source && row.destination);
  return <section className="flow-experience" aria-label="Network flow exploration">
    {replay && <div className="replay-controls"><p>Sequential historical records. Playback speed is for demonstration; it does not reproduce original packet timing.</p>
      <div className="analysis-result-actions"><button onClick={() => { if (position >= analysis.total_flows) setPosition(0); setPlaying(value => !value); }}>{playing ? 'Pause replay' : 'Play replay'}</button><button onClick={() => { setPlaying(false); setPosition(0); }}>Restart replay</button><label>Playback speed <select value={speed} onChange={event => setSpeed(Number(event.target.value))}>{[0.5, 1, 2, 4].map(value => <option key={value} value={value}>{value}&times;</option>)}</select></label></div>
      <label className="replay-progress">Replay position <input type="range" min="0" max={analysis.total_flows} value={position} onChange={event => { setPlaying(false); setPosition(Number(event.target.value)); }}/></label>
      <p role="status" aria-live={playing ? 'off' : 'polite'}>{position} / {analysis.total_flows} flows ? {position - malicious} normal ? {malicious} malicious</p>
    </div>}
    {hasTopology ? <><p>Connections from uploaded source and destination IP columns. Showing up to 40 devices and 80 directed connections; use the records table for the complete result.</p>
      <svg className="actual-topology" viewBox="0 0 900 480" role="img" aria-label="Observed flow connections. Select a device below to inspect connections.">
        <defs><marker id="flow-arrow" viewBox="0 0 10 10" refX="20" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/></marker></defs>
        {network.edges.map(edge => { const source = network.points.find(point => point.id === edge.source)!; const destination = network.points.find(point => point.id === edge.destination)!; return <path key={`${edge.source}>${edge.destination}`} d={edge.source === edge.destination ? `M ${source.x} ${source.y} c -45 -65 45 -65 0 0` : `M ${source.x} ${source.y} L ${destination.x} ${destination.y}`} className={edge.malicious ? 'malicious-edge' : 'normal-edge'} markerEnd="url(#flow-arrow)"/>; })}
        {network.points.map(point => <g key={point.id}><circle cx={point.x} cy={point.y} r={selected === point.id ? 12 : 8}/><text x={point.x} y={point.y + 25} textAnchor="middle">{point.id}</text></g>)}
      </svg>
      <label>Inspect device <select value={selected} onChange={event => setSelected(event.target.value)}><option value="">Select an IP address</option>{network.points.map(point => <option key={point.id}>{point.id}</option>)}</select></label>
      {selected && <ul className="connection-list">{network.edges.filter(edge => edge.source === selected || edge.destination === selected).map(edge => <li key={`${edge.source}>${edge.destination}`}>{edge.source} &rarr; {edge.destination}: {edge.count} flows, {edge.malicious} malicious classifications</li>)}</ul>}
    </> : <p>No device topology is available: this file has no source and destination IP pairs. Flow classifications below remain available. No device relationships are inferred from the model features.</p>}
  </section>;
}
