import type { AlarmEntry } from '../store/sessionStore';

interface AlarmTimelinePanelProps {
  alarms: AlarmEntry[];
}

export default function AlarmTimelinePanel({ alarms }: AlarmTimelinePanelProps) {
  return (
    <div className="glass-panel p-3 w-80 max-h-48 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up flex flex-col">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-2">告警时间线</h3>
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-1 min-h-0">
        {alarms.length === 0 ? (
          <div className="text-[11px] text-gray-500 font-mono">暂无告警</div>
        ) : (
          alarms.slice().reverse().map((alarm, index) => (
            <div key={`${alarm.tsNs}-${index}`} className="border border-white/5 rounded-lg p-2 bg-white/[0.02]">
              <div className="text-[10px] font-mono text-gray-500">{alarm.source} · {alarm.workflowStep || '-'}</div>
              <div className="text-[11px] font-mono text-white mt-1">{alarm.message}</div>
              <div className="text-[10px] font-mono mt-1 text-clinical-amber">
                {alarm.severity} · {alarm.autoAction || 'no-auto-action'}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
