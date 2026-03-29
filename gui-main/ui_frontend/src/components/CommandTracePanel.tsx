import type { CommandTraceEnvelope } from '../api/client';

export default function CommandTracePanel({ trace }: { trace: CommandTraceEnvelope | null }) {
  const entries = trace?.entries ?? [];
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Command Trace</h3>
      <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar text-[11px] font-mono text-white">
        {entries.length === 0 ? <div className="text-gray-500">暂无命令追踪</div> : entries.slice().reverse().slice(0, 12).map((entry, index) => (
          <div key={`${entry.ts_ns ?? index}-${entry.command ?? 'cmd'}`} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <div className="text-gray-300">{entry.command || '-'}</div>
            <div className="text-gray-500 mt-1">{entry.workflow_step || '-'} · {entry.auto_action || 'manual'}</div>
            <div className="text-gray-400 mt-1">{String(entry.reply?.message ?? '-')}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
