import { ReplayLibrary } from '../components/ReplayLibrary';
import { useAnalysis } from '../services/analysis';
import { AnalysisWorkspace } from '../components/AnalysisWorkspace';
import { ContextNote } from '../components/WorkspaceDetails';

export default function Pulse() {
  const analysis = useAnalysis();
  return <>
    {analysis
      ? <AnalysisWorkspace analysis={analysis} mode="Network Pulse"/>
      : <ContextNote>Run the bundled historical benchmark through the active model. Network topology is shown only when a dataset includes validated source and destination addresses.</ContextNote>}
    <ReplayLibrary/>
  </>;
}
