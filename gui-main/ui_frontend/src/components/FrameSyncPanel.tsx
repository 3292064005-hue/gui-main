import type { FrameSyncEnvelope } from '../api/client';

export default function FrameSyncPanel({ frameSync }: { frameSync: FrameSyncEnvelope | null }) {
  const rows = frameSync?.rows ?? [];
  const preview = rows.slice(0, 4);
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Frame Sync</h3>
      <div className="space-y-2 text-[11px] font-mono text-gray-200 max-h-48 overflow-y-auto custom-scrollbar">
        <div>Frames: {rows.length}</div>
        {preview.map((row, index) => (
          <div key={index} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <div>frame #{String(row.frame_id ?? index + 1)}</div>
            <div className="text-gray-400">segment {String(row.segment_id ?? '-')} · q {typeof row.quality_score === 'number' ? row.quality_score.toFixed(2) : '-'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
