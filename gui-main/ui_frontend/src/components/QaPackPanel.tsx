import type { QaPackEnvelope } from '../api/client';

export default function QaPackPanel({ qaPack }: { qaPack: QaPackEnvelope | null }) {
  const schemaCount = Object.keys(qaPack?.schemas ?? {}).length;
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">QA Pack</h3>
      <div className="space-y-2 text-[11px] font-mono text-gray-200">
        <div>Session Dir: {qaPack?.session_dir || '-'}</div>
        <div>Schemas: {schemaCount}</div>
        <div>Annotations: {qaPack?.annotations?.length ?? 0}</div>
        <div>Frame Sync: {qaPack?.frame_sync ? 'ready' : 'missing'}</div>
        <div>Compare: {qaPack?.compare ? 'ready' : 'missing'}</div>
        <div>Diagnostics: {qaPack?.diagnostics ? 'ready' : 'missing'}</div>
      </div>
    </div>
  );
}
