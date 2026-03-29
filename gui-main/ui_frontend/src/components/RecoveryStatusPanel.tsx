import type { HealthEnvelope } from '../api/client';
import type { AlarmEntry } from '../store/sessionStore';

function adviceFor(state: string | undefined): string {
  switch (state) {
    case 'ESTOP_LATCHED':
      return '保持设备静止，先排查故障后再由操作者解除。';
    case 'CONTROLLED_RETRACT':
      return '等待受控退让完成，检查接触力与路径偏差。';
    case 'HOLDING':
      return '当前处于保持状态，确认力与遥测恢复后再继续。';
    case 'RETRY_WAIT_STABLE':
      return '系统正在等待接触力重新稳定。';
    case 'RETRY_READY':
      return '恢复条件已满足，可由操作者决定是否继续。';
    default:
      return '系统恢复链空闲。';
  }
}

export default function RecoveryStatusPanel({ health, alarms }: { health: HealthEnvelope | null; alarms: AlarmEntry[] }) {
  const latest = alarms.length > 0 ? alarms[alarms.length - 1] : null;
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Recovery Status</h3>
      <div className="space-y-2 text-[11px] font-mono text-white">
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
          <div className="text-gray-400">State</div>
          <div className="mt-1">{health?.recovery_state || 'IDLE'}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
          <div className="text-gray-400">Advice</div>
          <div className="mt-1 text-gray-200">{adviceFor(health?.recovery_state)}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
          <div className="text-gray-400">Latest alarm</div>
          <div className="mt-1">{latest ? `${latest.severity} · ${latest.message}` : '无'}</div>
        </div>
      </div>
    </div>
  );
}
