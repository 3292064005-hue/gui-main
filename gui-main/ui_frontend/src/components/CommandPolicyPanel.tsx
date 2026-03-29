interface CommandPolicyPanelProps {
  catalog?: { policies?: Array<Record<string, unknown>> } | null;
  snapshot?: { execution_state?: string; contact_state?: string; plan_state?: string; resume_mode?: string; decision_count?: number } | null;
}

export default function CommandPolicyPanel({ catalog, snapshot }: CommandPolicyPanelProps) {
  const policies = Array.isArray(catalog?.policies) ? catalog!.policies!.slice(0, 8) : [];
  return (
    <div className="glass-panel p-3">
      <div className="text-xs font-mono text-clinical-cyan mb-2">COMMAND POLICY</div>
      {snapshot ? (
        <div className="mb-3 text-[10px] text-gray-500 font-mono space-y-1">
          <div>state: {snapshot.execution_state ?? '-'}</div>
          <div>contact: {snapshot.contact_state ?? '-'}</div>
          <div>plan: {snapshot.plan_state ?? '-'}</div>
          <div>resume: {snapshot.resume_mode ?? '-'}</div>
          <div>decisions: {snapshot.decision_count ?? 0}</div>
        </div>
      ) : null}
      {policies.length === 0 ? (
        <div className="text-[11px] text-gray-400 font-mono">暂无命令矩阵</div>
      ) : (
        <div className="space-y-2">
          {policies.map((item) => (
            <div key={String(item.command)} className="rounded-xl border border-white/10 p-2">
              <div className="text-[11px] font-mono text-white">{String(item.command)}</div>
              <div className="text-[10px] text-gray-400 font-mono">states: {Array.isArray(item.allowed_states) ? item.allowed_states.join(', ') : '*'}</div>
              <div className="text-[10px] text-gray-500 font-mono">fallback: {String(item.fallback_action ?? 'manual_review')}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
