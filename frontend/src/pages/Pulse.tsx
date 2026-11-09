import { useAnalysis } from '../services/analysis';
import { AnalysisWorkspace } from '../components/AnalysisWorkspace';
import { useEffect, useRef, useState } from 'react';
import { Pause, Play, RotateCcw } from 'lucide-react';
import { NetworkMap } from '../components/NetworkMap';
import { ContextNote } from '../components/WorkspaceDetails';
import { Panel } from '../components/ui';
import { usePreference } from '../hooks/preferences';

const duration = 48;
const steps = [
  { at: 0, device: 'workstation', title: 'Client request', route: 'Workstation → Gateway', detail: 'An illustrative client begins a connection through the gateway.' },
  { at: 12, device: 'dns', title: 'Name lookup', route: 'Workstation → DNS resolver', detail: 'A conceptual DNS path shows how a client could resolve a service name.' },
  { at: 24, device: 'server', title: 'Service connection', route: 'Gateway → Application server', detail: 'The diagram follows an example request to an application endpoint.' },
  { at: 36, device: 'remote', title: 'Second route', route: 'Gateway → Remote host', detail: 'A final example path shows another connection that an investigator could inspect.' },
] as const;
const speeds = [0.5, 1, 2] as const;
const devices = ['gateway', 'workstation', 'dns', 'server', 'remote'] as const;
type DeviceId = (typeof devices)[number];
const isDevice = (value: unknown): value is DeviceId => typeof value === 'string' && devices.includes(value as DeviceId);

function formatPosition(seconds: number) {
  const value = Math.floor(seconds);
  return `00:${String(value).padStart(2, '0')}`;
}

function SamplePulse() {
  const [elapsed, setElapsed] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof speeds)[number]>(1);
  const [selectedDevice, setSelectedDevice] = usePreference<DeviceId>('network-node', steps[0].device, isDevice);
  const stepIndex = Math.min(steps.length - 1, Math.floor(elapsed / (duration / steps.length)));
  const step = steps[stepIndex];
  const previousStep = useRef(stepIndex);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setElapsed((current) => Math.min(duration, current + speed * 0.25));
    }, 250);
    return () => window.clearInterval(timer);
  }, [playing, speed]);

  useEffect(() => {
    if (elapsed >= duration) setPlaying(false);
  }, [elapsed]);

  useEffect(() => {
    if (previousStep.current === stepIndex) return;
    previousStep.current = stepIndex;
    setSelectedDevice(steps[stepIndex].device);
  }, [setSelectedDevice, stepIndex]);

  function goToStep(index: number) {
    setPlaying(false);
    setElapsed(steps[index].at);
    setSelectedDevice(steps[index].device);
  }

  function chooseDevice(device: string) {
    if (!isDevice(device)) return;
    setSelectedDevice(device);
    const matchingStep = steps.find((item) => item.device === device);
    if (matchingStep) {
      setPlaying(false);
      setElapsed(matchingStep.at);
    }
  }

  function togglePlayback() {
    if (elapsed >= duration) setElapsed(0);
    setPlaying((value) => !value);
  }

  function restart() {
    setPlaying(false);
    setElapsed(0);
    setSelectedDevice(steps[0].device);
  }

  return <>
    <ContextNote>This is an illustrative local walkthrough, not a historical replay. The current API does not provide replay scenarios; no uploaded traffic, live capture, or ML predictions are represented here.</ContextNote>
    <Panel title="Illustrative replay preview" aside={<span className="tag">Sample UI data</span>}>
      <div className="replay-intro">
        <div>
          <h3>Follow a connection path</h3>
          <p>Use the timeline to step through a conceptual route. Real historical replay can replace this walkthrough when the replay API is available.</p>
        </div>
        <span className="replay-source">Local concept fixture</span>
      </div>

      <div className="replay-stage" role="status" aria-live="polite">
        <span className="replay-stage-index">Step {stepIndex + 1} of {steps.length}</span>
        <h3>{step.title}</h3>
        <strong>{step.route}</strong>
        <p>{step.detail}</p>
      </div>

      <div className="replay-controls" aria-label="Illustrative walkthrough controls">
        <div className="replay-buttons">
          <button className="primary" type="button" onClick={togglePlayback} aria-label={playing ? 'Pause walkthrough' : 'Play walkthrough'}>
            {playing ? <Pause size={16} /> : <Play size={16} />}{playing ? 'Pause' : 'Play'}
          </button>
          <button type="button" className="replay-restart" onClick={restart}><RotateCcw size={16} /> Restart</button>
          <label className="replay-speed">Playback speed
            <select value={speed} onChange={(event) => setSpeed(Number(event.target.value) as (typeof speeds)[number])}>
              {speeds.map((value) => <option key={value} value={value}>{value}×</option>)}
            </select>
          </label>
        </div>
        <label className="replay-position" htmlFor="walkthrough-position">
          <span>Walkthrough position</span>
          <input id="walkthrough-position" type="range" min="0" max={duration} step="1" value={elapsed} onChange={(event) => { setPlaying(false); setElapsed(Number(event.target.value)); }} />
          <output htmlFor="walkthrough-position">{formatPosition(elapsed)} / {formatPosition(duration)}</output>
        </label>
      </div>

      <ol className="replay-sequence" aria-label="Walkthrough steps">
        {steps.map((item, index) => <li key={item.device}>
          <button type="button" aria-pressed={stepIndex === index} onClick={() => goToStep(index)}>
            <span>{String(index + 1).padStart(2, '0')}</span>{item.title}
          </button>
        </li>)}
      </ol>

      <NetworkMap selectedDevice={selectedDevice} onDeviceSelect={chooseDevice} />
      <p className="fine">Conceptual topology only. Device links are illustrative and are not derived from an uploaded dataset.</p>
    </Panel>
  </>;
}

export default function Pulse() {
 const analysis = useAnalysis();
 return analysis ? <AnalysisWorkspace analysis={analysis} mode="Network Pulse" /> : <SamplePulse />;
}
