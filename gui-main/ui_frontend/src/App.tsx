import { lazy, startTransition, Suspense, useEffect, useMemo, useState } from 'react';
import {
  fetchCurrentAlarms,
  fetchCurrentAnnotations,
  fetchCurrentArtifacts,
  fetchCurrentAssessment,
  fetchCurrentCommandTrace,
  fetchCurrentCompare,
  fetchCurrentDiagnostics,
  fetchCurrentFrameSync,
  fetchCurrentPatientRegistration,
  fetchCurrentProfile,
  fetchCurrentQaPack,
  fetchCurrentQuality,
  fetchCurrentReadiness,
  fetchCurrentReplay,
  fetchCurrentReport,
  fetchCurrentScanProtocol,
  fetchCurrentSession,
  fetchCurrentTrends,
  fetchHealth,
  fetchProtocolSchema,
  postCommand,
  type CurrentSessionEnvelope,
  type DeviceReadinessEnvelope,
  type HealthEnvelope,
  type ProtocolSchema,
} from './api/client';
import { useTelemetryStore } from './store/telemetryStore';
import { useSessionStore } from './store/sessionStore';
import { useUIStore } from './store/uiStore';
import { useTelemetrySocket } from './hooks/useWebSocket';

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
    productUpdateTick,
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
    consumeProductTopics,
    setAlarmTimeline,
    setSessionReport,
    setReplayIndex,
    setQualityTimeline,
    setFrameSync,
    setArtifacts,
    setCompare,
    setTrends,
    setDiagnostics,
    setCommandTrace,
    setAssessment,
    setProfile,
    setPatientRegistration,
    setScanProtocol,
    setQaPack,
    setAnnotations,
  } = useSessionStore();
  const pendingProductTopics = useSessionStore((s) => s.pendingProductTopics);
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

  const commandAllowed = useMemo(() => {
    return (command: string) => {
      if (readOnlyMode || !operatorRole) return false;
      const preconditions = protocolSchema?.commands?.[command]?.state_preconditions as string[] | undefined;
      if (!preconditions || preconditions.length === 0) return true;
      return preconditions.includes('*') || preconditions.includes(executionState);
    };
  }, [executionState, operatorRole, protocolSchema, readOnlyMode]);

  const fireCommand = async (command: (typeof WRITE_COMMANDS)[number], successMessage: string) => {
    if (commandPending) return;
    if (!commandAllowed(command)) {
      addToast(`当前工作面或状态不允许执行 ${command}`, 'warn');
      return;
    }
    try {
      setCommandPending(true);
      const reply = await postCommand(command, {}, workspace);
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

  useEffect(() => {
    let cancelled = false;
    fetchProtocolSchema()
      .then((schema) => {
        if (!cancelled) startTransition(() => setProtocolSchema(schema));
      })
      .catch((error) => addLog('warn', `schema 加载失败: ${error instanceof Error ? error.message : 'unknown'}`));
    return () => {
      cancelled = true;
    };
  }, [addLog]);

  useEffect(() => {
    let cancelled = false;
    const sync = async () => {
      try {
        const [healthPayload, sessionPayload] = await Promise.all([fetchHealth(), fetchCurrentSession().catch(() => null)]);
        if (cancelled) return;
        startTransition(() => {
          setHealth(healthPayload);
          setCurrentSession(sessionPayload);
        });
        useSessionStore.getState().syncCoreState(healthPayload.execution_state, sessionPayload?.session_id ?? null, sessionPayload?.session_started_at ?? null);
        if (!sessionPayload) {
          startTransition(() => {
            setSessionReport(null);
            setReplayIndex(null);
            setQualityTimeline(null);
            setFrameSync(null);
            setArtifacts(null);
            setCompare(null);
            setTrends(null);
            setDiagnostics(null);
            setCommandTrace(null);
            setAssessment(null);
            setProfile(null);
            setPatientRegistration(null);
            setScanProtocol(null);
            setQaPack(null);
            setAnnotations([]);
            setReadiness(null);
            setAlarmTimeline(null);
          });
          return;
        }

        const changedTopics = consumeProductTopics();
        const fullSync = changedTopics.length === 0;
        const shouldFetch = (...topics: string[]) => fullSync || topics.some((topic) => changedTopics.includes(topic));

        const promises = await Promise.all([
          shouldFetch('report_updated') && sessionPayload.report_available ? fetchCurrentReport().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('replay_updated') && sessionPayload.replay_available ? fetchCurrentReplay().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('quality_updated', 'session_product_update') ? fetchCurrentQuality().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('frame_sync_updated') && sessionPayload.frame_sync_available ? fetchCurrentFrameSync().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('alarms_updated', 'session_product_update') ? fetchCurrentAlarms().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('artifact_ready', 'manifest_updated') ? fetchCurrentArtifacts().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('compare_updated') && sessionPayload.compare_available ? fetchCurrentCompare().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('trends_updated') && sessionPayload.trends_available ? fetchCurrentTrends().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('diagnostics_updated') && sessionPayload.diagnostics_available ? fetchCurrentDiagnostics().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('annotations_updated', 'session_product_update') ? fetchCurrentAnnotations().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('readiness_updated') && sessionPayload.readiness_available ? fetchCurrentReadiness().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('profile_updated') && sessionPayload.profile_available ? fetchCurrentProfile().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('registration_updated') && sessionPayload.patient_registration_available ? fetchCurrentPatientRegistration().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('scan_protocol_updated') && sessionPayload.scan_protocol_available ? fetchCurrentScanProtocol().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('qa_pack_updated') && sessionPayload.qa_pack_available ? fetchCurrentQaPack().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('command_trace_updated') && sessionPayload.command_trace_available ? fetchCurrentCommandTrace().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('assessment_updated') && sessionPayload.assessment_available ? fetchCurrentAssessment().catch(() => null) : Promise.resolve(undefined),
        ]);
        if (cancelled) return;
        const [report, replay, quality, frameSyncPayload, alarmPayload, artifactsPayload, comparePayload, trendsPayload, diagnosticsPayload, annotationsPayload, readinessPayload, profilePayload, registrationPayload, scanProtocolPayload, qaPayload, commandTracePayload, assessmentPayload] = promises;
        startTransition(() => {
          if (report !== undefined) setSessionReport(report ?? null);
          if (replay !== undefined) setReplayIndex(replay ?? null);
          if (quality !== undefined) setQualityTimeline(quality ?? null);
          if (frameSyncPayload !== undefined) setFrameSync(frameSyncPayload ?? null);
          if (alarmPayload !== undefined) setAlarmTimeline(alarmPayload ?? null);
          if (artifactsPayload !== undefined) setArtifacts(artifactsPayload ?? null);
          if (comparePayload !== undefined) setCompare(comparePayload ?? null);
          if (trendsPayload !== undefined) setTrends(trendsPayload ?? null);
          if (diagnosticsPayload !== undefined) setDiagnostics(diagnosticsPayload ?? null);
          if (annotationsPayload !== undefined) setAnnotations(annotationsPayload?.annotations ?? []);
          if (readinessPayload !== undefined) setReadiness(readinessPayload ?? null);
          if (profilePayload !== undefined) setProfile(profilePayload ?? null);
          if (registrationPayload !== undefined) setPatientRegistration(registrationPayload ?? null);
          if (scanProtocolPayload !== undefined) setScanProtocol(scanProtocolPayload ?? null);
          if (qaPayload !== undefined) setQaPack(qaPayload ?? null);
          if (commandTracePayload !== undefined) setCommandTrace(commandTracePayload ?? null);
          if (assessmentPayload !== undefined) setAssessment(assessmentPayload ?? null);
        });
      } catch (error) {
        addLog('warn', `headless 健康检查失败: ${error instanceof Error ? error.message : 'unknown'}`);
      }
    };
    void sync();
    const interval = window.setInterval(sync, workspace === 'researcher' ? 3500 : 2000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [addLog, consumeProductTopics, pendingProductTopics, productUpdateTick, setAlarmTimeline, setAnnotations, setArtifacts, setAssessment, setCommandTrace, setCompare, setDiagnostics, setFrameSync, setPatientRegistration, setProfile, setQaPack, setQualityTimeline, setReplayIndex, setScanProtocol, setSessionReport, setTrends, workspace]);

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
