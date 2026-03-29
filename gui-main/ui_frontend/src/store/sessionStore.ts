import type {
  AlarmTimelineEnvelope,
  AnnotationEntry,
  ArtifactsEnvelope,
  AssessmentEnvelope,
  CommandTraceEnvelope,
  DiagnosticsPackEnvelope,
  FrameSyncEnvelope,
  PatientRegistrationEnvelope,
  QaPackEnvelope,
  QualityTimelineEnvelope,
  ReplayIndexEnvelope,
  ScanProtocolEnvelope,
  SessionCompareEnvelope,
  SessionReportEnvelope,
  SessionTrendsEnvelope,
  XMateProfileEnvelope,
} from '../api/client';
import { create } from 'zustand';

export interface LogEntry {
  time: string;
  level: 'info' | 'warn' | 'error' | 'success';
  msg: string;
}

export interface AlarmEntry {
  tsNs: number;
  severity: string;
  source: string;
  message: string;
  workflowStep?: string;
  requestId?: string;
  autoAction?: string;
}

type ScanState = 'idle' | 'scanning' | 'paused' | 'halted';

interface SessionState {
  scanState: ScanState;
  executionState: string;
  sessionId: string | null;
  sessionStartedAt: string | null;
  startTime: number | null;
  frameCount: number;
  productUpdateTick: number;
  pendingProductTopics: string[];
  logs: LogEntry[];
  alarms: AlarmEntry[];
  alarmTimeline: AlarmTimelineEnvelope | null;
  sessionReport: SessionReportEnvelope | null;
  replayIndex: ReplayIndexEnvelope | null;
  qualityTimeline: QualityTimelineEnvelope | null;
  frameSync: FrameSyncEnvelope | null;
  artifacts: ArtifactsEnvelope | null;
  compare: SessionCompareEnvelope | null;
  trends: SessionTrendsEnvelope | null;
  diagnostics: DiagnosticsPackEnvelope | null;
  commandTrace: CommandTraceEnvelope | null;
  assessment: AssessmentEnvelope | null;
  profile: XMateProfileEnvelope | null;
  patientRegistration: PatientRegistrationEnvelope | null;
  scanProtocol: ScanProtocolEnvelope | null;
  qaPack: QaPackEnvelope | null;
  annotations: AnnotationEntry[];
  forceHistory: { t: number; v: number }[];
  setExecutionState: (executionState: string) => void;
  triggerHalt: () => void;
  resetHalt: () => void;
  markProductUpdate: (topics?: string[]) => void;
  consumeProductTopics: () => string[];
  addLog: (level: LogEntry['level'], msg: string) => void;
  pushAlarm: (alarm: AlarmEntry) => void;
  setAlarmTimeline: (timeline: AlarmTimelineEnvelope | null) => void;
  setSessionReport: (report: SessionReportEnvelope | null) => void;
  setReplayIndex: (replay: ReplayIndexEnvelope | null) => void;
  setQualityTimeline: (quality: QualityTimelineEnvelope | null) => void;
  setFrameSync: (frameSync: FrameSyncEnvelope | null) => void;
  setArtifacts: (artifacts: ArtifactsEnvelope | null) => void;
  setCompare: (compare: SessionCompareEnvelope | null) => void;
  setTrends: (trends: SessionTrendsEnvelope | null) => void;
  setDiagnostics: (diagnostics: DiagnosticsPackEnvelope | null) => void;
  setCommandTrace: (commandTrace: CommandTraceEnvelope | null) => void;
  setAssessment: (assessment: AssessmentEnvelope | null) => void;
  setProfile: (profile: XMateProfileEnvelope | null) => void;
  setPatientRegistration: (registration: PatientRegistrationEnvelope | null) => void;
  setScanProtocol: (protocol: ScanProtocolEnvelope | null) => void;
  setQaPack: (qaPack: QaPackEnvelope | null) => void;
  setAnnotations: (annotations: AnnotationEntry[]) => void;
  pushForce: (v: number) => void;
  incrementFrame: () => void;
  syncCoreState: (executionState: string, sessionId?: string | null, sessionStartedAt?: string | null) => void;
  exportCSV: () => void;
}

const timeStr = () => {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}.${String(d.getMilliseconds()).padStart(3, '0')}`;
};

function deriveScanState(executionState: string): ScanState {
  if (executionState === 'SCANNING') return 'scanning';
  if (executionState === 'PAUSED_HOLD') return 'paused';
  if (executionState === 'ESTOP') return 'halted';
  return 'idle';
}

function parseBackendStart(sessionStartedAt?: string | null): number | null {
  if (!sessionStartedAt) return null;
  const parsed = Date.parse(sessionStartedAt.replace(' ', 'T'));
  return Number.isFinite(parsed) ? parsed : null;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  scanState: 'idle',
  executionState: 'BOOT',
  sessionId: null,
  sessionStartedAt: null,
  startTime: null,
  frameCount: 0,
  productUpdateTick: 0,
  pendingProductTopics: [],
  logs: [{ time: timeStr(), level: 'info', msg: '系统初始化完成，等待连接...' }],
  alarms: [],
  alarmTimeline: null,
  sessionReport: null,
  replayIndex: null,
  qualityTimeline: null,
  frameSync: null,
  artifacts: null,
  compare: null,
  trends: null,
  diagnostics: null,
  commandTrace: null,
  assessment: null,
  profile: null,
  patientRegistration: null,
  scanProtocol: null,
  qaPack: null,
  annotations: [],
  forceHistory: [],

  setExecutionState: (executionState) =>
    set((state) => {
      const scanState = deriveScanState(executionState);
      const startTime =
        scanState === 'scanning'
          ? state.startTime ?? parseBackendStart(state.sessionStartedAt) ?? Date.now()
          : executionState === 'RETREATING' || executionState === 'SCAN_COMPLETE'
            ? null
            : state.startTime;
      return { executionState, scanState, startTime };
    }),

  triggerHalt: () => {
    set({ executionState: 'ESTOP', scanState: 'halted' });
    get().addLog('error', '⚠ 紧急制动已激活 — 硬件锁定');
  },

  resetHalt: () => {
    set({ executionState: 'AUTO_READY', scanState: 'idle', startTime: null });
    get().addLog('warn', '制动已解除 — 系统恢复待机');
  },

  markProductUpdate: (topics = []) => set((s) => ({ productUpdateTick: s.productUpdateTick + 1, pendingProductTopics: Array.from(new Set([...s.pendingProductTopics, ...topics])) })),

  consumeProductTopics: () => {
    const topics = get().pendingProductTopics.slice();
    set({ pendingProductTopics: [] });
    return topics;
  },

  addLog: (level, msg) => {
    set((s) => ({ logs: [...s.logs.slice(-300), { time: timeStr(), level, msg }] }));
  },

  pushAlarm: (alarm) => {
    set((s) => ({ alarms: [...s.alarms.slice(-149), alarm] }));
  },

  setAlarmTimeline: (alarmTimeline) => set({ alarmTimeline }),
  setSessionReport: (sessionReport) => set({ sessionReport }),
  setReplayIndex: (replayIndex) => set({ replayIndex }),
  setQualityTimeline: (qualityTimeline) => set({ qualityTimeline }),
  setFrameSync: (frameSync) => set({ frameSync }),
  setArtifacts: (artifacts) => set({ artifacts }),
  setCompare: (compare) => set({ compare }),
  setTrends: (trends) => set({ trends }),
  setDiagnostics: (diagnostics) => set({ diagnostics }),
  setCommandTrace: (commandTrace) => set({ commandTrace }),
  setAssessment: (assessment) => set({ assessment }),
  setProfile: (profile) => set({ profile }),
  setPatientRegistration: (patientRegistration) => set({ patientRegistration }),
  setScanProtocol: (scanProtocol) => set({ scanProtocol }),
  setQaPack: (qaPack) => set({ qaPack }),
  setAnnotations: (annotations) => set({ annotations }),

  pushForce: (v) => {
    if (get().scanState !== 'scanning') return;
    set((s) => ({ forceHistory: [...s.forceHistory.slice(-3000), { t: Date.now(), v }] }));
  },

  incrementFrame: () => set((s) => ({ frameCount: s.frameCount + 1 })),

  syncCoreState: (executionState, sessionId, sessionStartedAt) =>
    set((state) => {
      const scanState = deriveScanState(executionState);
      const nextSessionId = sessionId === undefined ? state.sessionId : sessionId;
      const nextSessionStartedAt = sessionStartedAt === undefined ? state.sessionStartedAt : sessionStartedAt;
      const backendStartTime = parseBackendStart(nextSessionStartedAt);
      return {
        executionState,
        scanState,
        sessionId: nextSessionId,
        sessionStartedAt: nextSessionStartedAt,
        startTime:
          scanState === 'scanning'
            ? state.startTime ?? backendStartTime ?? Date.now()
            : executionState === 'RETREATING' || executionState === 'SCAN_COMPLETE'
              ? null
              : state.startTime,
      };
    }),

  exportCSV: () => {
    const frameSyncRows = get().frameSync?.rows ?? [];
    const rows =
      frameSyncRows.length > 0
        ? frameSyncRows
            .map((row) => ({
              t: typeof row.ts_ns === 'number' ? row.ts_ns / 1_000_000 : Date.now(),
              v:
                typeof row.pressure_current === 'number'
                  ? row.pressure_current
                  : typeof row.force_n === 'number'
                    ? row.force_n
                    : 0,
            }))
            .filter((row) => Number.isFinite(row.t))
        : get().forceHistory;
    if (rows.length === 0) return;
    const csv = 'timestamp_ms,force_N\n' + rows.map((r) => `${Math.round(r.t)},${r.v.toFixed(4)}`).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `force_data_${get().sessionId || 'export'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    get().addLog('success', `已导出 ${rows.length} 条力数据至 CSV`);
  },
}));
