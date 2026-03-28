import { lazy, startTransition, Suspense, useEffect, useMemo, useState } from 'react';
import {
  fetchCurrentReplay,
  fetchCurrentReport,
  fetchCurrentSession,
  fetchHealth,
  fetchProtocolSchema,
  postCommand,
  type CurrentSessionEnvelope,
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

import { Activity, AlertTriangle, Loader2, Play, ShieldAlert, Square, WifiOff, Zap } from 'lucide-react';

const ThreeDView = lazy(() => import('./components/ThreeDView'));
const ForceGraph = lazy(() => import('./components/ForceGraph'));
const RollingChart = lazy(() => import('./components/RollingChart'));
const CameraFeed = lazy(() => import('./components/CameraFeed'));
const UltrasoundFeed = lazy(() => import('./components/UltrasoundFeed'));
const JointAnglePanel = lazy(() => import('./components/JointAnglePanel'));
const SystemLog = lazy(() => import('./components/SystemLog'));

function PanelFallback({ className = '' }: { className?: string }) {
  return <div className={`glass-panel animate-pulse ${className}`} />;
}

export default function App() {
  useTelemetrySocket();
  const [commandPending, setCommandPending] = useState(false);
  const [protocolSchema, setProtocolSchema] = useState<ProtocolSchema | null>(null);
  const [health, setHealth] = useState<HealthEnvelope | null>(null);
  const [currentSession, setCurrentSession] = useState<CurrentSessionEnvelope | null>(null);

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
    setSessionReport,
    setReplayIndex,
  } = useSessionStore();
  const {
    showCamera,
    showUltrasound,
    showForceGraph,
    show3DView,
    showJoints,
    showLog,
    showReport,
    showAlarms,
    addToast,
  } = useUIStore();

  const isHalted = scanState === 'halted';
  const isScanning = scanState === 'scanning';
  const isPaused = scanState === 'paused';
  const desiredContactForce = protocolSchema?.force_control.desired_contact_force_n ?? 10.0;
  const maxZForce = protocolSchema?.force_control.max_z_force_n ?? 35.0;
  const staleTelemetryMs = protocolSchema?.force_control.stale_telemetry_ms ?? 250;
  const telemetryStale = health?.telemetry_stale ?? (connected && latencyMs > staleTelemetryMs);

  useEffect(() => {
    useTelemetryStore.getState().setTelemetryStale(telemetryStale);
  }, [telemetryStale]);

  const commandAllowed = useMemo(() => {
    return (command: string) => {
      const preconditions = protocolSchema?.commands?.[command]?.state_preconditions as string[] | undefined;
      if (!preconditions || preconditions.length === 0) {
        return true;
      }
      return preconditions.includes('*') || preconditions.includes(executionState);
    };
  }, [executionState, protocolSchema]);

  const handleScanToggle = async () => {
    if (isHalted || commandPending) {
      return;
    }
    const command = isScanning ? 'safe_retreat' : isPaused ? 'resume_scan' : 'start_scan';
    if (!commandAllowed(command)) {
      addToast(`当前状态不允许执行 ${command}`, 'warn');
      return;
    }
    const successMessage = isScanning ? '已请求安全退让' : isPaused ? '已请求恢复扫描' : '已请求开始扫描';
    try {
      setCommandPending(true);
      const reply = await postCommand(command);
      if (!reply.ok) {
        addLog('error', `${command} 失败: ${reply.message}`);
        addToast(reply.message || `${command} 失败`, 'error');
        return;
      }
      addLog('success', reply.message || successMessage);
      addToast(successMessage, isScanning ? 'info' : 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : `${command} failed`;
      addLog('error', `${command} 失败: ${message}`);
      addToast(message, 'error');
    } finally {
      setCommandPending(false);
    }
  };

  const handleEStop = async () => {
    if (commandPending || !commandAllowed('emergency_stop')) {
      return;
    }
    try {
      setCommandPending(true);
      const reply = await postCommand('emergency_stop');
      if (!reply.ok) {
        addLog('error', `emergency_stop 失败: ${reply.message}`);
        addToast(reply.message || '急停请求失败', 'error');
        return;
      }
      triggerHalt();
      addLog('error', reply.message || '急停请求已发送');
      addToast('紧急制动已激活', 'error');
    } catch (error) {
      const message = error instanceof Error ? error.message : '急停请求失败';
      addLog('error', `emergency_stop 失败: ${message}`);
      addToast(message, 'error');
    } finally {
      setCommandPending(false);
    }
  };

  const handleReset = async () => {
    if (commandPending || !commandAllowed('clear_fault')) {
      return;
    }
    try {
      setCommandPending(true);
      const reply = await postCommand('clear_fault');
      if (!reply.ok) {
        addLog('error', `clear_fault 失败: ${reply.message}`);
        addToast(reply.message || '故障清除失败', 'error');
        return;
      }
      resetHalt();
      addLog('warn', reply.message || '故障已清除');
      addToast('制动已解除，系统恢复', 'warn');
    } catch (error) {
      const message = error instanceof Error ? error.message : '故障清除失败';
      addLog('error', `clear_fault 失败: ${message}`);
      addToast(message, 'error');
    } finally {
      setCommandPending(false);
    }
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        void handleScanToggle();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        if (isHalted) void handleReset();
        else void handleEStop();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  useEffect(() => {
    let cancelled = false;
    fetchProtocolSchema()
      .then((schema) => {
        if (!cancelled) {
          startTransition(() => setProtocolSchema(schema));
        }
      })
      .catch((error) => {
        const message = error instanceof Error ? error.message : 'schema unavailable';
        addLog('warn', `schema 加载失败: ${message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [addLog]);

  useEffect(() => {
    let cancelled = false;
    const sync = async () => {
      try {
        const [healthPayload, sessionPayload] = await Promise.all([
          fetchHealth(),
          fetchCurrentSession().catch(() => null),
        ]);
        if (cancelled) {
          return;
        }
        startTransition(() => {
          setHealth(healthPayload);
          setCurrentSession(sessionPayload);
        });
        if (sessionPayload?.report_available) {
          const report = await fetchCurrentReport().catch(() => null);
          if (!cancelled) {
            startTransition(() => setSessionReport(report));
          }
        }
        if (sessionPayload?.replay_available) {
          const replay = await fetchCurrentReplay().catch(() => null);
          if (!cancelled) {
            startTransition(() => setReplayIndex(replay));
          }
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'health unavailable';
        addLog('warn', `headless 健康检查失败: ${message}`);
      }
    };
    void sync();
    const interval = window.setInterval(sync, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [addLog, executionState, setReplayIndex, setSessionReport, sessionId]);

  return (
    <div className="relative w-screen h-screen">
      <div className={`absolute inset-0 z-0 transition-opacity duration-500 ${show3DView && !isHalted ? 'opacity-100' : 'opacity-20'}`}>
        <Suspense fallback={<PanelFallback className="absolute inset-0" />}>
          {show3DView ? <ThreeDView targetForce={desiredContactForce} maxForce={maxZForce} /> : null}
        </Suspense>
      </div>

      <div className="absolute inset-0 z-10 pointer-events-none flex flex-col" style={{ paddingBottom: '28px' }}>
        <header className="flex justify-between items-center glass-panel p-3 mx-4 mt-4 pointer-events-auto shadow-[0_0_30px_rgba(0,0,0,0.6)]">
          <div className="flex items-center space-x-3">
            <Activity className={`w-5 h-5 animate-pulse-fast ${isHalted ? 'text-clinical-error' : 'text-clinical-cyan'}`} />
            <h1 className={`text-lg font-mono tracking-widest font-bold ${isHalted ? 'text-clinical-error' : 'text-clinical-cyan'}`}>
              脊柱超声机器人
            </h1>
            <span className="text-[10px] text-gray-600 font-mono">SPINE.US / ROKAE xMate ER3</span>
          </div>

          <div className="flex items-center space-x-4">
            <SessionTimer />
            {telemetryStale ? (
              <span className="font-mono text-xs flex items-center text-clinical-error">
                <AlertTriangle className="w-4 h-4 mr-1.5" /> 遥测陈旧
              </span>
            ) : null}
            {connected ? (
              <span className={`font-mono text-xs flex items-center ${isHalted ? 'text-clinical-error' : 'text-clinical-emerald'}`}>
                <div className={`w-1.5 h-1.5 rounded-full mr-1.5 animate-pulse ${isHalted ? 'bg-clinical-error' : 'bg-clinical-emerald'}`} />
                {isHalted ? '数据暂停' : '已同步'}
              </span>
            ) : (
              <span className="text-clinical-error font-mono text-xs flex items-center">
                <WifiOff className="w-4 h-4 mr-1.5" /> 离线
              </span>
            )}
          </div>
        </header>

        <div className={`flex flex-1 mt-3 px-4 pointer-events-none min-h-0 transition-opacity duration-300 ${isHalted ? 'opacity-30' : ''}`}>
          <Sidebar />
          <div className="flex-1" />
          <div className="flex flex-col items-end space-y-0 pointer-events-none max-h-full overflow-y-auto custom-scrollbar pr-1">
            <Suspense fallback={<PanelFallback className="w-[320px] h-[180px]" />}>
              {showCamera ? <CameraFeed /> : null}
            </Suspense>
            <Suspense fallback={<PanelFallback className="w-[320px] h-[180px] mt-3" />}>
              {showUltrasound ? <UltrasoundFeed /> : null}
            </Suspense>
            {showJoints ? (
              <div className="mt-3">
                <Suspense fallback={<PanelFallback className="w-[320px] h-[160px]" />}>
                  <JointAnglePanel />
                </Suspense>
              </div>
            ) : null}
          </div>
        </div>

        <div className={`flex justify-between items-end px-4 pb-2 mt-2 pointer-events-none transition-opacity duration-300 ${isHalted ? 'opacity-30' : ''}`}>
          <div className="flex items-end space-x-3 pointer-events-auto">
            {showForceGraph ? (
              <div className="w-80 glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up">
                <h3 className="text-[10px] text-gray-500 font-bold tracking-widest mb-3">Z 轴力控</h3>
                <Suspense fallback={<PanelFallback className="w-full h-[180px]" />}>
                  <ForceGraph latestForce={force} maxForce={maxZForce} targetForce={desiredContactForce} />
                </Suspense>
              </div>
            ) : null}

            {showForceGraph ? (
              <div className="glass-panel p-2 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up">
                <h3 className="text-[10px] text-clinical-cyan font-bold tracking-widest px-1 mb-1">力传感器示波器</h3>
                <Suspense fallback={<PanelFallback className="w-[300px] h-[100px]" />}>
                  <RollingChart
                    latestValue={force}
                    color={
                      Math.abs(force - desiredContactForce) < 1.0
                        ? '#00FA9A'
                        : Math.abs(force - desiredContactForce) < 3.0
                          ? '#FFB800'
                          : '#FF2A55'
                    }
                    maxVal={maxZForce}
                    targetValue={desiredContactForce}
                    width={300}
                    height={100}
                  />
                </Suspense>
              </div>
            ) : null}

            {showLog ? (
              <Suspense fallback={<PanelFallback className="w-80 h-48" />}>
                <SystemLog />
              </Suspense>
            ) : null}

            {showReport ? (
              <SessionReportPanel sessionId={sessionId} report={sessionReport} replay={replayIndex} />
            ) : null}

            {showAlarms ? <AlarmTimelinePanel alarms={alarms} /> : null}
          </div>

          <div className="glass-panel p-2 flex space-x-2 pointer-events-auto shadow-[0_0_20px_rgba(0,0,0,0.5)]">
            <button
              onClick={() => void handleScanToggle()}
              disabled={isHalted || commandPending || !commandAllowed(isScanning ? 'safe_retreat' : isPaused ? 'resume_scan' : 'start_scan')}
              className={`px-6 py-3 border rounded-xl font-bold text-sm tracking-wider transition-all hover:scale-105 active:scale-95 flex items-center justify-center min-w-[150px] disabled:opacity-30 disabled:cursor-not-allowed
                ${isScanning
                  ? 'bg-clinical-emerald/15 border-clinical-emerald/40 text-clinical-emerald hover:bg-clinical-emerald/30'
                  : 'bg-clinical-cyan/15 border-clinical-cyan/40 text-clinical-cyan hover:bg-clinical-cyan/30'}`}
            >
              {commandPending ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> 处理中</>
              ) : isScanning ? (
                <><Square className="w-4 h-4 mr-2" /> 安全退让</>
              ) : isPaused ? (
                <><Play className="w-4 h-4 mr-2" /> 恢复扫描</>
              ) : (
                <><Play className="w-4 h-4 mr-2" /> 开始扫描</>
              )}
            </button>
            <button
              onClick={() => void handleEStop()}
              disabled={commandPending || !commandAllowed('emergency_stop')}
              className="px-6 py-3 bg-clinical-error/15 hover:bg-clinical-error/30 border border-clinical-error/40
                         rounded-xl font-bold text-sm tracking-wider transition-all hover:scale-105 active:scale-95
                         min-w-[130px] text-clinical-error flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Zap className="w-4 h-4 mr-2" /> 紧急制动
            </button>
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
            <div className="flex items-center space-x-2 text-white/60 text-xs font-mono">
              <span>按 ESC 键</span>
              <span>或点击下方按钮解除</span>
            </div>
            <button
              onClick={() => void handleReset()}
              className="px-8 py-3 bg-white text-clinical-error font-bold tracking-widest rounded-xl hover:bg-gray-100 transition-all hover:scale-105 active:scale-95 text-sm"
            >
              解除制动 (OVERRIDE)
            </button>
          </div>
        </div>
      ) : null}

      <StatusBar />
      <ToastContainer />
    </div>
  );
}
