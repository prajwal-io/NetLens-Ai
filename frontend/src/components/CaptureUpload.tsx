import { useState, type FormEvent } from 'react';
import { ArrowDownToLine, Upload } from 'lucide-react';
import { api, type CaptureAnalysis } from '../services/api';
import { Panel } from './ui';

const maxBytes = 5 * 1024 * 1024;

export function CaptureUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<CaptureAnalysis | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    if (!/\.pcap(ng)?$/i.test(file.name) || !file.size || file.size > maxBytes) {
      setError(!file.size ? 'The capture is empty.' : file.size > maxBytes ? 'Capture files are limited to 5 MiB.' : 'Choose a .pcap or .pcapng file.');
      return;
    }
    setBusy(true); setError(''); setResult(null);
    try { setResult(await api.analyzeCapture(file)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Capture analysis failed.'); }
    finally { setBusy(false); }
  }

  return <Panel title="Packet capture" className="capture-panel" aside={<span className="tag">PCAP / PCAPNG</span>}>
    <p className="description">Upload a bounded capture file to extract TCP/UDP flow counts, endpoints, byte totals, and durations. The file is processed in memory and is not saved.</p>
    <div className="capture-demo-file"><a href="/demo-capture.pcap" download><ArrowDownToLine size={15}/> Download synthetic 5-packet sample</a><small>Uses reserved documentation IP addresses; contains no real user traffic.</small></div>
    <form className="capture-form" onSubmit={event => void submit(event)}>
      <label htmlFor="capture-file">Capture file</label>
      <input id="capture-file" type="file" accept=".pcap,.pcapng,application/vnd.tcpdump.pcap,application/x-pcapng" onChange={event => { setFile(event.target.files?.[0] ?? null); setError(''); setResult(null); }}/>
      <button className="primary" type="submit" disabled={!file || busy}><Upload size={16}/>{busy ? 'Reading capture...' : 'Analyze packet flows'}</button>
    </form>
    {error && <p className="error" role="alert">{error}</p>}
    {result && <section className="capture-result" aria-live="polite">
      <h3>{result.filename}</h3>
      <div className="capture-metrics"><div><span>Packets</span><strong>{result.packets_seen.toLocaleString()}</strong></div><div><span>TCP/UDP packets</span><strong>{result.supported_packets.toLocaleString()}</strong></div><div><span>Bidirectional flows</span><strong>{result.flow_count.toLocaleString()}</strong></div><div><span>Captured bytes</span><strong>{result.captured_bytes.toLocaleString()}</strong></div></div>
      {result.flows.length ? <div className="table-scroll" role="region" aria-label="Packet-derived flows" tabIndex={0}><table><caption>Showing {result.flows.length} of {result.flow_count} packet-derived flows. These are not model classifications.</caption><thead><tr><th scope="col">Source</th><th scope="col">Destination</th><th scope="col">Protocol</th><th scope="col">Packets A ↔ B</th><th scope="col">Bytes</th><th scope="col">Duration</th></tr></thead><tbody>{result.flows.map((flow, index) => <tr key={`${flow.source}-${flow.destination}-${index}`}><td><code>{flow.source}</code></td><td><code>{flow.destination}</code></td><td>{flow.protocol}</td><td>{flow.source_packets} ↔ {flow.destination_packets}</td><td>{flow.captured_bytes.toLocaleString()}</td><td>{flow.duration_seconds.toFixed(3)} s</td></tr>)}</tbody></table></div> : <p className="fine">No TCP/UDP IPv4/IPv6 flows were found in this capture.</p>}
      <ul className="capture-limitations">{result.limitations.map(item => <li key={item}>{item}</li>)}</ul>
    </section>}
  </Panel>;
}
