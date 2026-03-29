import type { SessionTrendsEnvelope } from '../api/client';

export default function TrendAnalysisPanel({ trends }: { trends: SessionTrendsEnvelope | null }) {
  const trendEntries = Object.entries(trends?.trends ?? {}).slice(0, 8);
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Trend Analysis</h3>
      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-gray-200">
        {trendEntries.length === 0 ? <div className="text-gray-500">暂无趋势数据</div> : trendEntries.map(([key, value]) => (
          <div key={key} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <div className="text-gray-400">{key}</div>
            <div>{String(value)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
