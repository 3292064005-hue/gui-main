import type { ArtifactsEnvelope, CurrentSessionEnvelope, DiagnosticsPackEnvelope, DeviceReadinessEnvelope, HealthEnvelope, SessionTrendsEnvelope } from '../api/client';

interface SessionConsolePanelProps {
  session: CurrentSessionEnvelope | null;
  health: HealthEnvelope | null;
  artifacts: ArtifactsEnvelope | null;
  trends: SessionTrendsEnvelope | null;
  diagnostics: DiagnosticsPackEnvelope | null;
  readiness: DeviceReadinessEnvelope | null;
}

function valueText(value: unknown): string {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? `${value}` : value.toFixed(2);
  }
  if (typeof value === 'boolean') {
    return value ? 'yes' : 'no';
  }
  if (typeof value === 'string') {
    return value || '-';
  }
  return '-';
}

export default function SessionConsolePanel({ session, health, artifacts, trends, diagnostics, readiness }: SessionConsolePanelProps) {
  const registryCount = Object.keys(artifacts?.artifact_registry ?? {}).length;
  const algorithmCount = Object.keys(artifacts?.algorithm_registry ?? {}).length;
  const trendQuality = trends?.trends?.avg_quality_score;
  const staleSamples = diagnostics?.telemetry_summary?.stale_samples;
  const readinessOk = readiness?.ready_to_lock;

  return (
    <div className="glass-panel p-3 w-80 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-2">会话控制台</h3>
      <div className="space-y-1 text-[11px] font-mono text-gray-300">
        <div>Session: {session?.session_id || '-'}</div>
        <div>执行状态: {health?.execution_state || '-'}</div>
        <div>恢复状态: {health?.recovery_state || '-'}</div>
        <div>会话锁定: {health?.session_locked ? 'yes' : 'no'}</div>
        <div>机械臂: {health?.robot_model || 'xmate_er3'}</div>
        <div>力传感器: {health?.force_sensor_provider || '-'}</div>
        <div>构建号: {health?.build_id || '-'}</div>
        <div>产物数量: {registryCount}</div>
        <div>算法阶段: {algorithmCount}</div>
        <div>质量趋势 Δ: {valueText(trendQuality)}</div>
        <div>陈旧样本: {valueText(staleSamples)}</div>
        <div>Readiness: {valueText(readinessOk)}</div>
      </div>
    </div>
  );
}
