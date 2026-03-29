import type { SelectedExecutionRationaleEnvelope } from '../api/client';

export default function SelectedExecutionRationalePanel({ rationale }: { rationale: SelectedExecutionRationaleEnvelope | null }) {
  if (!rationale) return null;
  const ranking = rationale.ranking_snapshot ?? [];
  return (
    <div className="glass-panel p-3 rounded-2xl border border-white/10">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-mono text-white">Execution Rationale</h3>
        <span className="text-xs font-mono text-clinical-cyan">{rationale.selected_plan_id ?? '-'}</span>
      </div>
      <div className="text-[11px] text-gray-400 font-mono space-y-1">
        <div>candidate count: {ranking.length}</div>
        <div>selected: {rationale.selected_candidate_id ?? rationale.selected_plan_id ?? '-'}</div>
        {(rationale.rejected_candidate_reasons ?? []).slice(0, 3).map((item) => <div key={item}>• {item}</div>)}
      </div>
    </div>
  );
}
