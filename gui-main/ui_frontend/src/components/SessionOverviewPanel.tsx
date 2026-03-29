import type { CurrentSessionEnvelope, DeviceReadinessEnvelope, SessionReportEnvelope, XMateProfileEnvelope } from '../api/client';

function metric(label: string, value: string | number | null | undefined) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
      <div className="text-gray-400 text-[10px] uppercase tracking-wide">{label}</div>
      <div className="text-white text-[11px] font-mono mt-1">{value ?? '-'}</div>
    </div>
  );
}

export default function SessionOverviewPanel({
  session,
  readiness,
  profile,
  report,
}: {
  session: CurrentSessionEnvelope | null;
  readiness: DeviceReadinessEnvelope | null;
  profile: XMateProfileEnvelope | null;
  report: SessionReportEnvelope | null;
}) {
  const overview = report?.session_overview ?? {};
  const quality = report?.quality_summary ?? {};
  const readyCount = [
    readiness?.robot_ready,
    readiness?.camera_ready,
    readiness?.ultrasound_ready,
    readiness?.force_provider_ready,
    readiness?.storage_ready,
    readiness?.network_link_ok,
  ].filter(Boolean).length;

  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Session Overview</h3>
      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
        {metric('Session', session?.session_id)}
        {metric('Started', session?.session_started_at ? new Date(session.session_started_at.replace(' ', 'T')).toLocaleString() : '-')}
        {metric('Robot', String(profile?.robot_model ?? overview['robot_model'] ?? '-'))}
        {metric('Axis', String(profile?.axis_count ?? overview['axis_count'] ?? '-'))}
        {metric('Readiness OK', `${readyCount}/6`)}
        {metric('Avg Quality', String(quality['avg_quality_score'] ?? '-'))}
        {metric('Coverage', String(quality['coverage_ratio'] ?? '-'))}
        {metric('Usable Sync', String(quality['usable_sync_ratio'] ?? '-'))}
      </div>
    </div>
  );
}
