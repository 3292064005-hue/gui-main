import type { QualityTimelineEnvelope } from '../api/client';

function buildRecommendations(quality: QualityTimelineEnvelope | null) {
  const points = quality?.points ?? [];
  const flagged = points.filter((point) => Boolean(point['need_resample']) || Boolean(point['stale_telemetry']) || String(point['force_status'] ?? '').includes('RETRACT'));
  const grouped = new Map<number, string[]>();
  for (const point of flagged.slice(0, 24)) {
    const segment = typeof point['segment_id'] === 'number' ? point['segment_id'] : 0;
    const reasons = grouped.get(segment) ?? [];
    if (Boolean(point['need_resample'])) reasons.push('image unusable');
    if (Boolean(point['stale_telemetry'])) reasons.push('telemetry stale');
    if (String(point['force_status'] ?? '').includes('RETRACT')) reasons.push('force recovery');
    grouped.set(segment, Array.from(new Set(reasons)));
  }
  return Array.from(grouped.entries()).slice(0, 8);
}

export default function RescanRecommendationPanel({ quality }: { quality: QualityTimelineEnvelope | null }) {
  const recommendations = buildRecommendations(quality);
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Rescan Recommendation</h3>
      <div className="space-y-2 text-[11px] font-mono text-white max-h-56 overflow-y-auto custom-scrollbar">
        {recommendations.length === 0 ? <div className="text-gray-500">当前无明确重扫建议</div> : recommendations.map(([segment, reasons]) => (
          <div key={segment} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <div className="text-gray-300">Segment {segment}</div>
            <div className="text-gray-400 mt-1">{reasons.join(' · ') || 'review suggested'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
