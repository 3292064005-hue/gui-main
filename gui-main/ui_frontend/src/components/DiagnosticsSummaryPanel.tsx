import type { DiagnosticsPackEnvelope } from '../api/client';

export default function DiagnosticsSummaryPanel({ diagnostics }: { diagnostics: DiagnosticsPackEnvelope | null }) {
  const summary = diagnostics?.summary ?? {};
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Diagnostics</h3>
      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-gray-200">
        {Object.entries(summary).slice(0, 8).map(([key, value]) => (
          <div key={key} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <div className="text-gray-400">{key}</div>
            <div>{String(value)}</div>
          </div>
        ))}
        {Object.keys(summary).length === 0 ? <div className="text-gray-500">暂无诊断摘要</div> : null}
      </div>
    </div>
  );
}
