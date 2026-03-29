import type { ContractKernelDiffEnvelope } from '../api/client';

export default function ContractKernelDiffPanel({ payload }: { payload: ContractKernelDiffEnvelope | null }) {
  if (!payload) return null;
  const consistent = payload.summary?.consistent ?? false;
  const diffs = payload.diffs ?? [];
  return (
    <div className="glass-panel p-3 rounded-2xl border border-white/10">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-mono text-white">Contract Kernel Diff</h3>
        <span className={`text-xs font-mono ${consistent ? 'text-clinical-emerald' : 'text-clinical-amber'}`}>{consistent ? 'ALIGNED' : 'DRIFT'}</span>
      </div>
      <div className="text-[11px] text-gray-400 font-mono space-y-1">
        <div>checks: {payload.summary?.checked_object_count ?? 0}</div>
        <div>diffs: {payload.summary?.diff_count ?? 0}</div>
        {diffs.slice(0, 3).map((item, idx) => (
          <div key={idx} className="text-clinical-amber">• {String(item.name ?? item.reason ?? 'diff')}</div>
        ))}
      </div>
    </div>
  );
}
