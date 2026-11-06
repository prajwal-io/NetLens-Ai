import { NetworkMap } from '../components/NetworkMap';
import { Panel } from '../components/ui';
export default function Pulse(){
 return <Panel title="Explore the connections" aside={<span className="tag">Conceptual / sample only</span>}><p className="description">Select a device to follow an illustrative connection. This diagram explains network relationships; it does not represent uploaded traffic or live packet capture.</p><NetworkMap/><p className="fine">Historical replay and model-connected topology are planned for Phase 4. Actual device relationships will only be displayed when source and destination fields exist.</p></Panel>
}
