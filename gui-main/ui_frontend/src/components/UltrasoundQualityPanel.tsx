import type { QualityTimelineEnvelope } from '../api/client';

export default function UltrasoundQualityPanel({ quality }: { quality: QualityTimelineEnvelope | null }) {
  const summary = quality?.summary ?? {};
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Ultrasound Quality</h3>
      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-gray-200">
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">Coverage</div><div>{typeof summary.coverage_ratio === 'number' ? `${(summary.coverage_ratio * 100).toFixed(1)}%` : '-'}</div></div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">Avg Quality</div><div>{typeof summary.avg_quality_score === 'number' ? summary.avg_quality_score.toFixed(2) : '-'}</div></div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">Resample</div><div>{String(summary.resample_events ?? '-')}</div></div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">Usable</div><div>{String(summary.usable_frame_count ?? '-')}</div></div>
      </div>
    </div>
  );
}
