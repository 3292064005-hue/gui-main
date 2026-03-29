import type { ReplayIndexEnvelope, SessionReportEnvelope } from '../api/client';

interface SessionReportPanelProps {
  sessionId: string | null;
  report: SessionReportEnvelope | null;
  replay: ReplayIndexEnvelope | null;
}

export default function SessionReportPanel({ sessionId, report, replay }: SessionReportPanelProps) {
  const qualitySummary = report?.quality_summary || {};
  const replaySummary = report?.replay || {};
  const operatorActions = report?.operator_actions || {};
  const replayStreams = replay?.streams || {};
  const cameraFrames = Number(
    replaySummary.camera_frames ??
      ((replayStreams.camera as { frame_count?: number } | undefined)?.frame_count ?? 0),
  );
  const ultrasoundFrames = Number(
    replaySummary.ultrasound_frames ??
      ((replayStreams.ultrasound as { frame_count?: number } | undefined)?.frame_count ?? 0),
  );

  return (
    <div className="glass-panel p-3 w-80 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-2">会话报告</h3>
      <div className="space-y-1 text-[11px] font-mono text-gray-300">
        <div>Session: {sessionId || '-'}</div>
        <div>平均质量: {Number(qualitySummary.avg_quality_score ?? 0).toFixed(2)}</div>
        <div>覆盖比例: {(Number(qualitySummary.coverage_ratio ?? 0) * 100).toFixed(1)}%</div>
        <div>重采样事件: {Number(qualitySummary.resample_events ?? 0)}</div>
        <div>相机帧数: {cameraFrames}</div>
        <div>超声帧数: {ultrasoundFrames}</div>
        <div>操作命令数: {Number(operatorActions.command_count ?? 0)}</div>
      </div>
    </div>
  );
}
