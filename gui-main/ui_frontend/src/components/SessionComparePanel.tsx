import type { SessionCompareEnvelope } from '../api/client';

function entriesOf(obj: Record<string, number | string> | undefined): Array<[string, number | string]> {
  return Object.entries(obj ?? {}).slice(0, 8);
}

export default function SessionComparePanel({ compare }: { compare: SessionCompareEnvelope | null }) {
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Session Compare</h3>
      <div className="space-y-3 text-[11px] font-mono text-gray-200">
        <div>Baseline: {compare?.baseline_session_id || 'fleet'}</div>
        <div className="grid grid-cols-2 gap-2">
          {entriesOf(compare?.delta_vs_baseline).map(([key, value]) => (
            <div key={key} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
              <div className="text-gray-400">{key}</div>
              <div>{String(value)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
