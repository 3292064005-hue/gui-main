import type { CurrentSessionEnvelope, DiagnosticsPackEnvelope, QaPackEnvelope, ReplayIndexEnvelope, SessionReportEnvelope } from '../api/client';

export default function ExportCenterPanel({
  session,
  report,
  replay,
  diagnostics,
  qaPack,
  onExportForceCsv,
}: {
  session: CurrentSessionEnvelope | null;
  report: SessionReportEnvelope | null;
  replay: ReplayIndexEnvelope | null;
  diagnostics: DiagnosticsPackEnvelope | null;
  qaPack: QaPackEnvelope | null;
  onExportForceCsv: () => void;
}) {
  const items: Array<{ label: string; ready: boolean }> = [
    { label: 'Session report', ready: Boolean(report) },
    { label: 'Replay index', ready: Boolean(replay) },
    { label: 'Diagnostics pack', ready: Boolean(diagnostics) },
    { label: 'QA pack', ready: Boolean(qaPack) },
    { label: 'Artifact registry', ready: Boolean(session?.artifact_registry && Object.keys(session.artifact_registry).length > 0) },
  ];
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Export Center</h3>
      <div className="space-y-2 text-[11px] font-mono text-white">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <span>{item.label}</span>
            <span className={item.ready ? 'text-clinical-emerald' : 'text-gray-500'}>{item.ready ? 'ready' : 'missing'}</span>
          </div>
        ))}
        <button onClick={onExportForceCsv} className="mt-2 w-full rounded-lg border border-clinical-emerald/30 bg-clinical-emerald/10 px-3 py-2 text-clinical-emerald hover:bg-clinical-emerald/20 transition-all">
          导出力数据 CSV
        </button>
      </div>
    </div>
  );
}
