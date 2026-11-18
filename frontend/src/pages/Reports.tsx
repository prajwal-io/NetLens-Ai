import { useAnalysis } from '../services/analysis';
import { AnalysisWorkspace } from '../components/AnalysisWorkspace';
import { ContextNote, NextStep } from '../components/WorkspaceDetails';
import { Empty, Panel } from '../components/ui';

export default function Reports() {
  const analysis = useAnalysis();
  return analysis
    ? <AnalysisWorkspace analysis={analysis} mode="Reports"/>
    : <>
      <ContextNote>CSV and PDF reports are generated from saved model analyses, so the exports match the classifications and totals shown in the workspace.</ContextNote>
      <Panel title="Reports follow an analysis">
        <Empty title="No analysis selected">Open a saved analysis above or run one to prepare its classification CSV and PDF report.</Empty>
        <NextStep title="Run the analysis pipeline" description="Upload a compatible flow CSV, validate it, then run the model." to="/traffic-analyzer" label="Open Traffic Analyzer"/>
      </Panel>
    </>;
}
