import type { ReleaseGateDecisionEnvelope } from '../api/client';

export default function ReleaseGatePanel({ decision }: { decision: ReleaseGateDecisionEnvelope | null }) {
  if (!decision) return null;
  const blocking = decision.blocking_reasons ?? [];
  const warnings = decision.warning_reasons ?? [];
  return (
    <div className="glass-panel p-3 rounded-2xl border border-white/10">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-mono text-white">Release Gate</h3>
        <span className={`text-xs font-mono ${decision.release_allowed ? 'text-clinical-emerald' : 'text-clinical-amber'}`}>{decision.release_allowed ? 'PASS' : 'HOLD'}</span>
      </div>
      <div className="text-[11px] text-gray-400 font-mono space-y-1">
        <div>blocking: {blocking.length}</div>
        <div>warnings: {warnings.length}</div>
        {blocking.slice(0, 3).map((item) => <div key={item} className="text-clinical-error">• {item}</div>)}
        {warnings.slice(0, 3).map((item) => <div key={item} className="text-clinical-amber">• {item}</div>)}
      </div>
    </div>
  );
}
