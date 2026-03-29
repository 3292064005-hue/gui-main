import type { DeviceReadinessEnvelope, PatientRegistrationEnvelope, ScanProtocolEnvelope, XMateProfileEnvelope } from '../api/client';

function line(label: string, value: string | number | boolean | null | undefined) {
  return (
    <div className="flex items-start justify-between gap-3 text-[11px] font-mono">
      <span className="text-gray-400">{label}</span>
      <span className="text-white text-right break-all">{value === undefined || value === null || value === '' ? '-' : String(value)}</span>
    </div>
  );
}

export default function LockFreezePanel({
  profile,
  readiness,
  registration,
  protocol,
}: {
  profile: XMateProfileEnvelope | null;
  readiness: DeviceReadinessEnvelope | null;
  registration: PatientRegistrationEnvelope | null;
  protocol: ScanProtocolEnvelope | null;
}) {
  const passCount = protocol?.path_policy && typeof protocol.path_policy === 'object' ? (protocol.path_policy as Record<string, unknown>).expected_pass_count : undefined;
  const overlap = protocol?.path_policy && typeof protocol.path_policy === 'object' ? (protocol.path_policy as Record<string, unknown>).strip_overlap_mm : undefined;
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Lock Freeze</h3>
      <div className="space-y-2">
        {line('Robot model', profile?.robot_model)}
        {line('SDK class', profile?.sdk_robot_class)}
        {line('RT tolerance %', profile?.rt_network_tolerance_percent)}
        {line('Ready to lock', readiness?.ready_to_lock)}
        {line('Control authority', readiness?.control_authority)}
        {line('Registration quality', registration?.registration_quality)}
        {line('Strip overlap', overlap as number | string | undefined)}
        {line('Expected passes', passCount as number | string | undefined)}
      </div>
    </div>
  );
}
