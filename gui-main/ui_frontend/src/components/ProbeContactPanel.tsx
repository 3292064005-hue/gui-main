export default function ProbeContactPanel({ force, targetForce, telemetryStale, recoveryState }: { force: number; targetForce: number; telemetryStale: boolean; recoveryState: string | undefined }) {
  const delta = Math.abs(force - targetForce);
  const stable = !telemetryStale && delta < 2.0;
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Probe Contact</h3>
      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">当前力</div><div className="text-white">{force.toFixed(2)} N</div></div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">目标力</div><div className="text-white">{targetForce.toFixed(2)} N</div></div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">稳定性</div><div className={stable ? 'text-clinical-emerald' : 'text-clinical-amber'}>{stable ? 'stable' : 'watch'}</div></div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">恢复状态</div><div className="text-white">{recoveryState || '-'}</div></div>
      </div>
    </div>
  );
}
