import type { PatientRegistrationEnvelope } from '../api/client';

export default function PatientRegistrationPanel({ registration }: { registration: PatientRegistrationEnvelope | null }) {
  const landmarks = registration?.landmarks ?? [];
  const corridor = registration?.scan_corridor as Record<string, unknown> | undefined;
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Patient Registration</h3>
      <div className="space-y-2 text-[11px] font-mono text-gray-200">
        <div>来源: {String(registration?.source ?? '-')}</div>
        <div>配准质量: {typeof registration?.registration_quality === 'number' ? registration.registration_quality.toFixed(2) : '-'}</div>
        <div>Landmarks: {landmarks.length}</div>
        <div>Corridor Length: {corridor && typeof corridor.length_mm === 'number' ? `${corridor.length_mm} mm` : '-'}</div>
        <div>Corridor Width: {corridor && typeof corridor.width_mm === 'number' ? `${corridor.width_mm} mm` : '-'}</div>
      </div>
    </div>
  );
}
