import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, CircleAlert, Globe2, ShieldAlert } from 'lucide-react';
import { Panel } from '../components/ui';
import { api, type UrlReputation } from '../services/api';

const samples = [
  { label: 'Lookalike brand', url: 'https://paypal-security.example/login' },
  { label: 'Lookalike character swap', url: 'https://paypa1.example/login' },
  { label: 'Plain HTTP + IP host', url: 'http://192.0.2.44/account/verify' },
  { label: 'IPv6 address host', url: 'https://[2001:db8::44]/login' },
  { label: 'No common signals', url: 'https://www.paypal.com/signin' },
];
const brands: Record<string, string[]> = { paypal: ['paypal.com'], google: ['google.com'], microsoft: ['microsoft.com'], amazon: ['amazon.com'] };

function isNearMatch(label: string, brand: string) {
  if (Math.abs(label.length - brand.length) > 1) return false;
  let left = 0;
  let right = 0;
  let edits = 0;
  while (left < label.length && right < brand.length) {
    if (label[left] === brand[right]) { left++; right++; continue; }
    if (++edits > 1) return false;
    if (label.length > brand.length) left++;
    else if (brand.length > label.length) right++;
    else { left++; right++; }
  }
  return edits + (left < label.length || right < brand.length ? 1 : 0) <= 1;
}

function inspectUrl(value: string) {
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Use an http:// or https:// URL.');
  if (url.username || url.password) throw new Error('Credentials in URLs are not supported for this demo.');
  const host = url.hostname.toLowerCase().replace(/\.$/, '');
  const findings: string[] = [];
  if (url.protocol === 'http:') findings.push('The address uses HTTP, so the connection is not encrypted.');
  if (host.startsWith('xn--') || host.includes('.xn--')) findings.push('The hostname contains punycode, which can represent lookalike characters.');
  const ipHost = /^\d{1,3}(?:\.\d{1,3}){3}$/.test(host) || (host.startsWith('[') && host.endsWith(']'));
  if (ipHost) {
    findings.push('The site uses an IP address instead of a recognizable domain name.');
    if (/^(?:10\.|127\.|169\.254\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)/.test(host) || host === '::1' || host.startsWith('[::1]')) {
      findings.push('The address is loopback or private, so it is not a public website address.');
    }
  }
  if (host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local') || host.endsWith('.internal')) {
    findings.push('The hostname is reserved for local or private networks.');
  }
  if (host.split('.').length > 4) findings.push('The hostname has many subdomain levels that can obscure the registered domain.');
  for (const [brand, domains] of Object.entries(brands)) {
    const official = domains.some((domain) => host === domain || host.endsWith(`.${domain}`));
    const normalized = host.replaceAll('0', 'o').replaceAll('1', 'l');
    const labels = host.split('.');
    if (!official && host.includes(brand)) {
      findings.push(`The hostname uses “${brand}” but is outside its common ${domains[0]} domain.`);
    } else if (!official && normalized.includes(brand)) {
      findings.push(`The hostname resembles “${brand}” with a 0/o or 1/l character swap and is outside its common ${domains[0]} domain.`);
    } else if (!official && labels.some((label) => isNearMatch(label, brand))) {
      findings.push(`A hostname label is one character away from “${brand}” and is outside its common ${domains[0]} domain.`);
    }
  }
  if (url.href.length > 120) findings.push('The address is unusually long and may hide its important parts.');
  return { host, findings };
}

export default function UrlCheck() {
  const [value, setValue] = useState('');
  const [result, setResult] = useState<ReturnType<typeof inspectUrl> | null>(null);
  const [error, setError] = useState('');
  const [reputation, setReputation] = useState<UrlReputation | null>(null);
  const [providerError, setProviderError] = useState('');
  const [providerBusy, setProviderBusy] = useState(false);
  function check(next = value) {
    setValue(next);
    setError('');
    setResult(null);
    setReputation(null);
    setProviderError('');
    if (!next.trim() || next.length > 2048) { setError(next.length > 2048 ? 'Enter a URL under 2,048 characters.' : 'Enter a URL to inspect.'); return; }
    try { setResult(inspectUrl(next.trim())); } catch { setError('Enter a valid URL beginning with http:// or https://.'); }
  }
  async function checkReputation() {
    setProviderBusy(true); setProviderError(''); setReputation(null);
    try { setReputation(await api.checkUrlReputation(value.trim())); }
    catch (reason) { setProviderError(reason instanceof Error ? reason.message : 'The live reputation check failed.'); }
    finally { setProviderBusy(false); }
  }
  const verdict = result && (result.findings.length > 1 ? 'Review carefully' : result.findings.length ? 'Warning signs found' : 'No common warning signs');
  return <div className="url-check-page">
    <Panel title="Inspect a URL" aside={<span className="url-check-local"><Globe2 size={14}/> Structural checks run locally</span>}>
      <div className="url-check-body">
        <p>Review local URL structure for signals that may indicate a spoofed or misleading address. This checker does not contact the website, resolve DNS, or follow redirects.</p>
        <form onSubmit={(event) => { event.preventDefault(); check(); }} className="url-check-form">
          <label htmlFor="url-check-input">Website address</label>
          <div className="url-check-input-row"><input id="url-check-input" type="url" inputMode="url" placeholder="https://example.com" value={value} onChange={(event) => { setValue(event.target.value); setReputation(null); setProviderError(''); }} aria-describedby="url-check-note"/><button type="submit">Inspect URL</button></div>
          <small id="url-check-note">Local checks review hostname and URL structure. The optional cached feed checks known phishing URLs; neither check proves a URL is safe.</small>
        </form>
        <div className="url-check-samples" aria-label="Demo examples">{samples.map((sample) => <button type="button" key={sample.label} onClick={() => check(sample.url)}>{sample.label}</button>)}</div>
        {error && <p className="url-check-error" role="alert">{error}</p>}
        {result && <section className="url-check-result" aria-live="polite">
          <div className="url-check-verdict"><span className={result.findings.length ? 'has-findings' : 'no-findings'}>{result.findings.length ? <ShieldAlert size={18}/> : <CheckCircle2 size={18}/>}</span><div><h3>{verdict}</h3><p>Checked hostname: <code>{result.host}</code></p></div></div>
          <h4>Evidence</h4>{result.findings.length ? <ul>{result.findings.map((finding) => <li key={finding}><CircleAlert size={15}/>{finding}</li>)}</ul> : <p>No common warning patterns were found. This does not guarantee the site is trustworthy.</p>}
        </section>}
        {result && <section className="url-reputation" aria-label="OpenPhish community feed lookup">
          <h3>Phishing feed lookup</h3>
          <p>The backend caches the OpenPhish community feed for up to 12 hours and compares this URL locally. Your URL is not sent to OpenPhish. The feed covers known phishing URLs only.</p>
          <button type="button" disabled={providerBusy} onClick={() => void checkReputation()}>{providerBusy ? 'Checking feed...' : 'Check OpenPhish feed'}</button>
          {providerError && <p className="url-check-error" role="alert">{providerError}</p>}
          {reputation && <div className={reputation.matched ? 'url-reputation-result flagged' : 'url-reputation-result'} role="status">
            {reputation.matched
              ? <><strong>OpenPhish lists this URL as {reputation.threat_types.join(', ')}.</strong><span>Treat this as an investigation signal and do not open the URL.</span></>
              : <><strong>No exact match in the OpenPhish community feed.</strong><span>No match does not mean the URL is safe.</span></>}
            <small>{reputation.stale ? 'Using a cached feed; refresh is overdue.' : 'Feed cached at'} {new Date(reputation.updated_at).toLocaleString()}.</small>
          </div>}
        </section>}
      </div>
    </Panel>
    <p className="url-check-flow-link">A URL does not contain packet data. To inspect benchmark flow records and packet counts, <Link to="/network-pulse">run a historical flow replay</Link> or <Link to="/traffic-analyzer">upload a PCAP capture</Link>.</p>
    <p className="url-check-disclaimer"><strong>Judge demo:</strong> Structural checks are transparent heuristics, not a trained URL classifier. The OpenPhish feed covers listed phishing URLs only; a missing match is not proof of safety. URL evidence is separate from the network-flow IDS model.</p>
  </div>;
}
