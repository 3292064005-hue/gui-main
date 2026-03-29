import { lazy, Suspense, useEffect, useState } from 'react';
import {
  postCommand,
  type CurrentSessionEnvelope,
  type DeviceReadinessEnvelope,
  type HealthEnvelope,
  type ProtocolSchema,
  type WorkspaceRole,
} from './api/client';
import { useTelemetryStore } from './store/telemetryStore';
import { useSessionStore } from './store/sessionStore';
import { useUIStore, type Workspace } from './store/uiStore';
import { useTelemetrySocket } from './hooks/useWebSocket';
import { useHeadlessSessionSync } from './hooks/useHeadlessSessionSync';
import { useCommandPolicySync } from './hooks/useCommandPolicySync';
import Sidebar from './components/Sidebar';
import SessionTimer from './components/SessionTimer';
import StatusBar from './components/StatusBar';
import ToastContainer from './components/Toast';
import SessionReportPanel from './components/SessionReportPanel';
import AlarmTimelinePanel from './components/AlarmTimelinePanel';
import SessionConsolePanel from './components/SessionConsolePanel';
import SystemReadinessPanel from './components/SystemReadinessPanel';
import PatientRegistrationPanel from './components/PatientRegistrationPanel';
import ScanProtocolPanel from './components/ScanProtocolPanel';
import ProbeContactPanel from './components/ProbeContactPanel';
import UltrasoundQualityPanel from './components/UltrasoundQualityPanel';
import DiagnosticsSummaryPanel from './components/DiagnosticsSummaryPanel';
import SessionComparePanel from './components/SessionComparePanel';
import TrendAnalysisPanel from './components/TrendAnalysisPanel';
import FrameSyncPanel from './components/FrameSyncPanel';
import QaPackPanel from './components/QaPackPanel';
import ArtifactExplorerPanel from './components/ArtifactExplorerPanel';
import SessionOverviewPanel from './components/SessionOverviewPanel';
import LockFreezePanel from './components/LockFreezePanel';
import RecoveryStatusPanel from './components/RecoveryStatusPanel';
import RescanRecommendationPanel from './components/RescanRecommendationPanel';
import CommandTracePanel from './components/CommandTracePanel';
import ArtifactDependencyPanel from './components/ArtifactDependencyPanel';
import AssessmentReviewDesk from './components/AssessmentReviewDesk';
import CommandPolicyPanel from './components/CommandPolicyPanel';
import ReleaseGatePanel from './components/ReleaseGatePanel';
import SelectedExecutionRationalePanel from './components/SelectedExecutionRationalePanel';
import ContractKernelDiffPanel from './components/ContractKernelDiffPanel';
import ExportCenterPanel from './components/ExportCenterPanel';
import { Activity, AlertTriangle, Loader2, Power, RefreshCw, ShieldAlert, WifiOff, Zap } from 'lucide-react';

const CameraFeed = lazy(() => import('./components/CameraFeed'));
const UltrasoundFeed = lazy(() => import('./components/UltrasoundFeed'));
const ForceGraph = lazy(() => import('./components/ForceGraph'));
const RollingChart = lazy(() => import('./components/RollingChart'));
const ThreeDView = lazy(() => import('./components/ThreeDView'));
const JointAnglePanel = lazy(() => import('./components/JointAnglePanel'));
const SystemLog = lazy(() => import('./components/SystemLog'));

function PanelFallback({ className = '' }: { className?: string }) {
  return <div className={`glass-panel animate-pulse ${className}`} />;
}

const WRITE_COMMANDS = ['connect_robot', 'power_on', 'set_auto_mode', 'validate_setup', 'start_scan', 'resume_scan', 'safe_retreat', 'emergency_stop', 'clear_fault'] as const;

function workspaceToRole(workspace: Workspace): WorkspaceRole {
  switch (workspace) {
    case 'review':
      return 'reviewer';
    case 'qa':
      return 'service';
    case 'researcher':
      return 'researcher';
    case 'operator':
    default:
      return 'operator';
  }
}

export default function App() {
  const workspace = useUIStore((s) => s.workspace);
  useTelemetrySocket(workspace);

  const [commandPending, setCommandPending] = useState(false);
  const [protocolSchema, setProtocolSchema] = useState<ProtocolSchema | null>(null);
  const [health, setHealth] = useState<HealthEnvelope | null>(null);
  const [currentSession, setCurrentSession] = useState<CurrentSessionEnvelope | null>(null);
  const [readiness, setReadiness] = useState<DeviceReadinessEnvelope | null>(null);

  const { force, connected, latencyMs } = useTelemetryStore();
  const {
    scanState,
    executionState,
    sessionId,
    triggerHalt,
    resetHalt,
    addLog,
    alarms,
    sessionReport,
    replayIndex,
    qualityTimeline,
    frameSync,
    artifacts,
    compare,
    trends,
    diagnostics,
    profile,
    patientRegistration,
    scanProtocol,
    qaPack,
    commandTrace,
    assessment,
    selectedExecutionRationale,
    releaseGateDecision,
    commandPolicySnapshot,
    contractKernelDiff,
  } = useSessionStore();
  const exportCSV = useSessionStore((s) => s.exportCSV);
  const {
    showCamera,
    showUltrasound,
    showForceGraph,
    show3DView,
    showJoints,
    showLog,
    showReport,
    showAlarms,
    showConsole,
    addToast,
  } = useUIStore();

  const isHalted = scanState === 'halted';
  const isScanning = scanState === 'scanning';
  const isPaused = scanState === 'paused';
  const desiredContactForce = protocolSchema?.force_control.desired_contact_force_n ?? 10.0;
  const maxZForce = protocolSchema?.force_control.max_z_force_n ?? 35.0;
  const staleTelemetryMs = protocolSchema?.force_control.stale_telemetry_ms ?? 250;
  const telemetryStale = health?.telemetry_stale ?? (connected && latencyMs > staleTelemetryMs);
  const readOnlyMode = health?.read_only_mode ?? false;
  const effectiveSessionId = currentSession?.session_id ?? sessionId;
  const operatorRole = workspace === 'operator';
  useEffect(() => {
    useTelemetryStore.getState().setTelemetryStale(telemetryStale);
  }, [telemetryStale]);


  const { commandPolicyCatalog, commandAllowed } = useCommandPolicySync({
    workspace,
    executionState,
    contactState: String((health as Record<string, unknown> | null)?.contact_state ?? 'UNKNOWN'),
    planState: currentSession?.scan_protocol_available ? 'execution_plan_loaded' : 'preview_plan_ready',
    resumeMode: diagnostics?.summary?.resume_mode ? String(diagnostics.summary.resume_mode) : (scanState === 'paused' ? 'segment_restart' : 'initial_start'),
    readOnlyMode,
  });


  const fireCommand = async (command: (typeof WRITE_COMMANDS)[number], successMessage: string) => {
    if (commandPending) return;
    if (!commandAllowed(command)) {
      addToast(`当前工作面或状态不允许执行 ${command}`, 'warn');
      return;
    }
    try {
      setCommandPending(true);
      const reply = await postCommand(command, {}, workspaceToRole(workspace));
      if (!reply.ok) {
        addLog('error', `${command} 失败: ${reply.message}`);
        addToast(reply.message || `${command} 失败`, 'error');
        return;
      }
      if (command === 'emergency_stop') triggerHalt();
      if (command === 'clear_fault') resetHalt();
      addLog('success', reply.message || successMessage);
      addToast(successMessage, command === 'safe_retreat' ? 'info' : 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : `${command} failed`;
      addLog('error', `${command} 失败: ${message}`);
      addToast(message, 'error');
    } finally {
      setCommandPending(false);
    }
  };


  useHeadlessSessionSync({ workspace, setProtocolSchema, setHealth, setCurrentSession, setReadiness });


  const commandButtons = (
    <div className="glass-panel p-2 flex flex-wrap gap-2 pointer-events-auto shadow-[0_0_20px_rgba(0,0,0,0.5)]">
      <button onClick={() => void fireCommand('connect_robot', '已请求连接机器人')} disabled={commandPending || !commandAllowed('connect_robot')} className="px-4 py-2 rounded-xl border border-white/10 text-xs font-mono disabled:opacity-30">连接</button>
      <button onClick={() => void fireCommand('power_on', '已请求机器人上电')} disabled={commandPending || !commandAllowed('power_on')} className="px-4 py-2 rounded-xl border border-white/10 text-xs font-mono disabled:opacity-30 flex items-center"><Power className="w-3 h-3 mr-1" />上电</button>
      <button onClick={() => void fireCommand('set_auto_mode', '已请求切换自动模式')} disabled={commandPending || !commandAllowed('set_auto_mode')} className="px-4 py-2 rounded-xl border border-white/10 text-xs font-mono disabled:opacity-30">自动</button>
      <button onClick={() => void fireCommand('validate_setup', '已请求校验设备就绪')} disabled={commandPending || !commandAllowed('validate_setup')} className="px-4 py-2 rounded-xl border border-white/10 text-xs font-mono disabled:opacity-30 flex items-center"><RefreshCw className="w-3 h-3 mr-1" />校验</button>
      <button onClick={() => void fireCommand(isScanning ? 'safe_retreat' : isPaused ? 'resume_scan' : 'start_scan', isScanning ? '已请求安全退让' : isPaused ? '已请求恢复扫描' : '已请求开始扫描')} disabled={commandPending || !commandAllowed(isScanning ? 'safe_retreat' : isPaused ? 'resume_scan' : 'start_scan')} className={`px-5 py-2 rounded-xl border text-xs font-mono disabled:opacity-30 ${isScanning ? 'border-clinical-emerald/30 text-clinical-emerald' : 'border-clinical-cyan/30 text-clinical-cyan'}`}>
        {commandPending ? <Loader2 className="w-3 h-3 animate-spin" /> : isScanning ? '安全退让' : isPaused ? '恢复扫描' : '开始扫描'}
      </button>
      <button onClick={() => void fireCommand('emergency_stop', '紧急制动已激活')} disabled={commandPending || !commandAllowed('emergency_stop')} className="px-5 py-2 rounded-xl border border-clinical-error/30 text-clinical-error text-xs font-mono disabled:opacity-30 flex items-center"><Zap className="w-3 h-3 mr-1" />急停</button>
      <button onClick={() => void fireCommand('clear_fault', '已请求清除故障')} disabled={commandPending || !commandAllowed('clear_fault')} className="px-4 py-2 rounded-xl border border-white/10 text-xs font-mono disabled:opacity-30">清故障</button>
    </div>
  );

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-clinical-surface">
      <div className={`absolute inset-0 z-0 transition-opacity duration-500 ${show3DView && !isHalted ? 'opacity-100' : 'opacity-20'}`}>
        <Suspense fallback={<PanelFallback className="absolute inset-0" />}>
          {show3DView ? <ThreeDView targetForce={desiredContactForce} maxForce={maxZForce} /> : null}
        </Suspense>
      </div>

      <div className="absolute inset-0 z-10 pointer-events-none flex flex-col" style={{ paddingBottom: '28px' }}>
        <header className="flex justify-between items-center glass-panel p-3 mx-4 mt-4 pointer-events-auto shadow-[0_0_30px_rgba(0,0,0,0.6)]">
          <div className="flex items-center space-x-3">
            <Activity className={`w-5 h-5 animate-pulse-fast ${isHalted ? 'text-clinical-error' : workspace === 'operator' ? 'text-clinical-cyan' : 'text-clinical-emerald'}`} />
            <h1 className={`text-lg font-mono tracking-widest font-bold ${isHalted ? 'text-clinical-error' : workspace === 'operator' ? 'text-clinical-cyan' : 'text-clinical-emerald'}`}>脊柱超声桌面工作台</h1>
            <span className="text-[10px] text-gray-600 font-mono">{workspace === 'operator' ? 'OPERATOR EXECUTION' : 'RESEARCH ANALYSIS'} / ROKAE xMate ER3</span>
          </div>
          <div className="flex items-center space-x-4">
            <SessionTimer />
            {telemetryStale ? <span className="font-mono text-xs flex items-center text-clinical-error"><AlertTriangle className="w-4 h-4 mr-1.5" />遥测陈旧</span> : null}
            {readOnlyMode ? <span className="font-mono text-xs flex items-center text-clinical-amber"><ShieldAlert className="w-4 h-4 mr-1.5" />只读评审模式</span> : null}
            {connected ? <span className={`font-mono text-xs flex items-center ${isHalted ? 'text-clinical-error' : 'text-clinical-emerald'}`}><div className={`w-1.5 h-1.5 rounded-full mr-1.5 animate-pulse ${isHalted ? 'bg-clinical-error' : 'bg-clinical-emerald'}`} />已同步</span> : <span className="text-clinical-error font-mono text-xs flex items-center"><WifiOff className="w-4 h-4 mr-1.5" />离线</span>}
          </div>
        </header>

        <div className="flex flex-1 min-h-0 mt-3 px-4 gap-3">
          <Sidebar />
          <div className="flex-1 min-h-0 pointer-events-auto overflow-y-auto custom-scrollbar pr-1">
            <div className="grid grid-cols-12 gap-3">
              {workspace === 'operator' ? (
                <>
                  <div className="col-span-3 space-y-3">
                    <SystemReadinessPanel readiness={readiness} />
                    <PatientRegistrationPanel registration={patientRegistration} />
                    <ScanProtocolPanel protocol={scanProtocol} />
                    <LockFreezePanel profile={profile} readiness={readiness} registration={patientRegistration} protocol={scanProtocol} />
                    <RecoveryStatusPanel health={health} alarms={alarms} />
                    <CommandPolicyPanel catalog={commandPolicyCatalog} snapshot={commandPolicySnapshot} />
                    <ContractKernelDiffPanel payload={contractKernelDiff} />
                    <ReleaseGatePanel decision={releaseGateDecision} />
                  </div>
                  <div className="col-span-6 space-y-3">
                    {showUltrasound ? <Suspense fallback={<PanelFallback className="h-[240px]" />}><UltrasoundFeed /></Suspense> : null}
                    {showCamera ? <Suspense fallback={<PanelFallback className="h-[220px]" />}><CameraFeed /></Suspense> : null}
                    {showForceGraph ? (
                      <div className="grid grid-cols-2 gap-3">
                        <Suspense fallback={<PanelFallback className="h-[200px]" />}><ForceGraph latestForce={force} maxForce={maxZForce} targetForce={desiredContactForce} /></Suspense>
                        <Suspense fallback={<PanelFallback className="h-[120px]" />}><RollingChart latestValue={force} maxVal={maxZForce} targetValue={desiredContactForce} width={320} height={120} color={Math.abs(force - desiredContactForce) < 1 ? '#00FA9A' : Math.abs(force - desiredContactForce) < 3 ? '#FFB800' : '#FF2A55'} /></Suspense>
                      </div>
                    ) : null}
                    <ProbeContactPanel force={force} targetForce={desiredContactForce} telemetryStale={telemetryStale} recoveryState={health?.recovery_state} />
                    <UltrasoundQualityPanel quality={qualityTimeline} />
                    <RescanRecommendationPanel quality={qualityTimeline} />
                  </div>
                  <div className="col-span-3 space-y-3">
                    {operatorRole ? commandButtons : null}
                    <ExportCenterPanel session={currentSession} report={sessionReport} replay={replayIndex} diagnostics={diagnostics} qaPack={qaPack} onExportForceCsv={exportCSV} />
                    {showReport ? <SessionReportPanel sessionId={effectiveSessionId} report={sessionReport} replay={replayIndex} /> : null}
                    {showAlarms ? <AlarmTimelinePanel alarms={alarms} /> : null}
                    {showConsole ? <SessionConsolePanel session={currentSession} health={health} artifacts={artifacts} trends={trends} diagnostics={diagnostics} readiness={readiness} /> : null}
                    {showJoints ? <Suspense fallback={<PanelFallback className="h-[200px]" />}><JointAnglePanel /></Suspense> : null}
                    {showLog ? <Suspense fallback={<PanelFallback className="h-[220px]" />}><SystemLog /></Suspense> : null}
                  </div>
                </>
              ) : (
                <>
                  <div className="col-span-3 space-y-3">
                    <SessionOverviewPanel session={currentSession} readiness={readiness} profile={profile} report={sessionReport} />
                    <SessionComparePanel compare={compare} />
                    <TrendAnalysisPanel trends={trends} />
                    <AssessmentReviewDesk assessment={assessment} />
                    {showConsole ? <SessionConsolePanel session={currentSession} health={health} artifacts={artifacts} trends={trends} diagnostics={diagnostics} readiness={readiness} /> : null}
                  </div>
                  <div className="col-span-6 space-y-3">
                    {showUltrasound ? <Suspense fallback={<PanelFallback className="h-[240px]" />}><UltrasoundFeed /></Suspense> : null}
                    <FrameSyncPanel frameSync={frameSync} />
                    {showReport ? <SessionReportPanel sessionId={effectiveSessionId} report={sessionReport} replay={replayIndex} /> : null}
                    {showAlarms ? <AlarmTimelinePanel alarms={alarms} /> : null}
                    <CommandTracePanel trace={commandTrace} />
                  </div>
                  <div className="col-span-3 space-y-3">
                    <QaPackPanel qaPack={qaPack} />
                    <ArtifactExplorerPanel artifacts={artifacts} />
                    <ArtifactDependencyPanel artifacts={artifacts} />
                    <DiagnosticsSummaryPanel diagnostics={diagnostics} />
                    <SelectedExecutionRationalePanel rationale={selectedExecutionRationale} />
                    <ReleaseGatePanel decision={releaseGateDecision} />
                    <CommandPolicyPanel catalog={commandPolicyCatalog} snapshot={commandPolicySnapshot} />
                    <ContractKernelDiffPanel payload={contractKernelDiff} />
                    <ReleaseGatePanel decision={releaseGateDecision} />
                    <PatientRegistrationPanel registration={patientRegistration} />
                    <ScanProtocolPanel protocol={scanProtocol} />
                    {showLog ? <Suspense fallback={<PanelFallback className="h-[220px]" />}><SystemLog /></Suspense> : null}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {isHalted ? (
        <div className="absolute inset-0 z-50 flex items-center justify-center pointer-events-auto bg-black/40 backdrop-blur-sm">
          <div className="bg-clinical-error/90 p-10 rounded-3xl backdrop-blur-3xl shadow-[0_0_120px_rgba(255,42,85,0.8)] flex flex-col items-center space-y-5 animate-pulse max-w-lg">
            <div className="flex items-center space-x-6">
              <ShieldAlert className="w-16 h-16 text-white" />
              <div>
                <h2 className="text-4xl font-extrabold tracking-tight text-white">紧急制动</h2>
                <p className="font-mono mt-2 text-base text-white/80">所有执行器已锁定，等待操作员确认</p>
              </div>
            </div>
            {operatorRole ? (
              <button onClick={() => void fireCommand('clear_fault', '制动已解除，系统恢复')} className="px-8 py-3 bg-white text-clinical-error font-bold tracking-widest rounded-xl hover:bg-gray-100 transition-all hover:scale-105 active:scale-95 text-sm">解除制动 (OVERRIDE)</button>
            ) : (
              <div className="text-white/80 font-mono text-sm">研究者工作面无权解除制动</div>
            )}
          </div>
        </div>
      ) : null}

      <StatusBar />
      <ToastContainer />
    </div>
  );
}
