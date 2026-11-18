import { useAnalysis } from '../services/analysis';
import { AnalysisWorkspace } from '../components/AnalysisWorkspace';
import { ContextNote, NextStep } from '../components/WorkspaceDetails';
import { Empty, Panel } from '../components/ui';

export default function Investigation() {
  const analysis = useAnalysis();
  return analysis
    ? <AnalysisWorkspace analysis={analysis} mode="Threat Investigation"/>
    : <>
      <ContextNote>Threat Investigation shows records returned by an uploaded analysis or historical replay. It does not use sample alerts.</ContextNote>
      <Panel title="Investigate model findings">
        <Empty title="Select or run an analysis">Open a saved result above, or analyze a compatible flow CSV to inspect its classifications and features.</Empty>
        <NextStep title="Start with traffic data" description="Validate the schema, then run the evaluated model." to="/traffic-analyzer" label="Open Traffic Analyzer"/>
      </Panel>
    </>;
}
