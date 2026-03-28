interface SessionReportPanelProps {
  sessionId: string | null;
  report: Record<string, unknown> | null;
  replay: Record<string, unknown> | null;
}

export default function SessionReportPanel({ sessionId, report, replay }: SessionReportPanelProps) {
  const qualitySummary = (report?.quality_summary as Record<string, unknown> | undefined) || {};
  const replaySummary = (report?.replay_summary as Record<string, unknown> | undefined) || {};

  return (
    <div className="glass-panel p-3 w-80 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-2">会话报告</h3>
      <div className="space-y-1 text-[11px] font-mono text-gray-300">
        <div>Session: {sessionId || '-'}</div>
        <div>平均质量: {Number(qualitySummary.avg_quality_score ?? 0).toFixed(2)}</div>
        <div>重采样事件: {Number(qualitySummary.resample_events ?? 0)}</div>
        <div>相机帧数: {Number(replaySummary.camera_frames ?? (replay?.streams as Record<string, unknown> | undefined)?.camera ? ((replay?.streams as Record<string, any>).camera.frame_count ?? 0) : 0)}</div>
        <div>超声帧数: {Number(replaySummary.ultrasound_frames ?? 0)}</div>
      </div>
    </div>
  );
}
