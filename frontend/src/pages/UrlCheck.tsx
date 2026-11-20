import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, CircleAlert, Globe2, ShieldAlert } from 'lucide-react';
import { Panel } from '../components/ui';
import { api, type URLCheck as URLCheckResult } from '../services/api';

const samples = [
  { label: 'Public website', url: 'https://example.com/' },
  { label: 'Suspicious path example', url: 'https://example.com/account/verify' },
];

export default function UrlCheck() {
  const [value, setValue] = useState('');
  const [result, setResult] = useState<URLCheckResult | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const requestId = useRef(0);

  async function check(next = value) {
    const url = next.trim();
    setValue(next);
    setError('');
    setResult(null);
    if (!url || url.length > 2048) {
      setError(url.length > 2048 ? 'Enter a URL under 2,048 characters.' : 'Enter a URL to inspect.');
      return;
    }
    const id = ++requestId.current;
    setBusy(true);
    try {
      const response = await api.checkUrl(url);
      if (id === requestId.current) setResult(response);
    } catch (reason) {
      if (id === requestId.current) setError(reason instanceof Error ? reason.message : 'The URL check failed. Please retry.');
    } finally {
      if (id === requestId.current) setBusy(false);
    }
  }

  const phishingSignal = result?.model.label === 'phishing_signal';
  const title = phishingSignal ? 'Phishing patterns detected' : 'No strong phishing pattern';
  return <div className="url-check-page">
    <Panel title="Inspect a URL" aside={<span className="url-check-local"><Globe2 size={14}/> Backend ML + live website check</span>}>
      <div className="url-check-body">
        <p>FastAPI validates the address, runs the URL-only machine learning model, then checks public DNS and the website’s HTTP response and redirects.</p>
        <form onSubmit={(event) => { event.preventDefault(); void check(); }} className="url-check-form">
          <label htmlFor="url-check-input">Website address</label>
          <div className="url-check-input-row"><input id="url-check-input" type="url" inputMode="url" placeholder="https://example.com" value={value} onChange={(event) => { setValue(event.target.value); setResult(null); setError(''); }} aria-describedby="url-check-note"/><button type="submit" disabled={busy}>{busy ? 'Analyzing…' : 'Inspect URL'}</button></div>
          <small id="url-check-note">Only public HTTP/HTTPS sites on ports 80 and 443 are checked. The probe sends a HEAD request and follows up to four redirects; it does not download page content.</small>
        </form>
        <div className="url-check-samples" aria-label="Live check examples">{samples.map((sample) => <button type="button" key={sample.label} disabled={busy} onClick={() => void check(sample.url)}>{sample.label}</button>)}</div>
        {busy && <div className="url-check-request" role="status"><span className="url-check-pulse"/> Sending the URL to FastAPI for analysis…</div>}
        {error && <p className="url-check-error" role="alert">{error}</p>}
        {result && <section className="url-check-result" aria-live="polite">
          <div className="url-check-verdict"><span className={phishingSignal ? 'has-findings' : 'no-findings'}>{phishingSignal ? <ShieldAlert size={18}/> : <CheckCircle2 size={18}/>}</span><div><h3>{title}</h3><p>Analyzed by <code>{result.model.model_version}</code> for <code>{result.host}</code></p></div></div>
          <div className={`url-model-score${phishingSignal ? '' : ' signal-low'}`}><span>Phishing signal score</span><strong>{(result.model.phishing_score * 100).toFixed(1)}%</strong><small>Model decision threshold {(result.model.threshold * 100).toFixed(1)}% · investigation signal, not a confirmed verdict</small></div>
          <h4>Completed backend stages</h4>
          <ol className="url-check-stages">{result.stages.map((stage, index) => <li key={stage.name} style={{ animationDelay: `${index * 90}ms` }}><span className="url-stage-node"/><span>{stage.name}</span><strong>{stage.duration_ms.toFixed(1)} ms</strong></li>)}</ol>
          <h4>Live website evidence</h4>
          <dl className="url-probe-details"><div><dt>DNS / HTTP</dt><dd>{result.probe.status === 'reachable' ? `Reachable · HTTP ${result.probe.http_status}` : result.probe.status === 'blocked' ? 'Blocked by network safety checks' : result.probe.status === 'redirect_limit' ? 'Redirect limit reached' : 'Could not complete'}</dd></div><div><dt>Public DNS addresses</dt><dd>{result.probe.dns_address_count}</dd></div><div><dt>Final hostname</dt><dd>{result.probe.final_host ?? 'Not reached'}</dd></div></dl>
          {result.probe.redirects.length > 0 && <div className="url-redirects"><strong>Redirect path</strong>{result.probe.redirects.map((redirect, index) => <p key={`${redirect.from_host}-${index}`}>HTTP {redirect.status}: <code>{redirect.from_host}</code> → <code>{redirect.to_host}</code>{redirect.cross_host ? ' · host changed' : ''}</p>)}</div>}
          <h4>Findings</h4><ul>{result.findings.map((finding) => <li key={finding}><CircleAlert size={15}/>{finding}</li>)}</ul>
          <details className="url-check-limitations"><summary>How to interpret this result</summary><ul>{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></details>
        </section>}
      </div>
    </Panel>
    <p className="url-check-flow-link">URL analysis does not contain packet data. To review packet counts and flow predictions, <Link to="/network-pulse">run a historical flow replay</Link> or <Link to="/traffic-analyzer">upload a PCAP capture</Link>.</p>
    <p className="url-check-disclaimer"><strong>Demo note:</strong> URL classification uses a separate URL-only model. It does not send URLs to a reputation feed, and a low score or successful HTTP response does not establish that a site is safe.</p>
  </div>;
}
