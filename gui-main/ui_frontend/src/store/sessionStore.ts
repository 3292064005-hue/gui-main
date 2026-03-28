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

interface SessionState {
  // Scan state
  scanState: 'idle' | 'scanning' | 'paused' | 'halted';
  executionState: string;
  sessionId: string | null;
  startTime: number | null;
  frameCount: number;

  // Event log
  logs: LogEntry[];
  alarms: AlarmEntry[];
  sessionReport: Record<string, unknown> | null;
  replayIndex: Record<string, unknown> | null;

  // Force history for CSV export
  forceHistory: { t: number; v: number }[];

  // Actions
  startScan: () => void;
  stopScan: () => void;
  triggerHalt: () => void;
  resetHalt: () => void;
  addLog: (level: LogEntry['level'], msg: string) => void;
  pushAlarm: (alarm: AlarmEntry) => void;
  setSessionReport: (report: Record<string, unknown> | null) => void;
  setReplayIndex: (replay: Record<string, unknown> | null) => void;
  pushForce: (v: number) => void;
  incrementFrame: () => void;
  syncCoreState: (executionState: string, sessionId?: string | null) => void;
  exportCSV: () => void;
}

const genSessionId = () => {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `SES-${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
};

const timeStr = () => {
  const d = new Date();
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}.${String(d.getMilliseconds()).padStart(3,'0')}`;
};

export const useSessionStore = create<SessionState>((set, get) => ({
  scanState: 'idle',
  executionState: 'BOOT',
  sessionId: null,
  startTime: null,
  frameCount: 0,
  logs: [{ time: timeStr(), level: 'info', msg: '系统初始化完成，等待连接...' }],
  alarms: [],
  sessionReport: null,
  replayIndex: null,
  forceHistory: [],

  startScan: () => {
    const sid = genSessionId();
    set({ scanState: 'scanning', executionState: 'SCANNING', sessionId: sid, startTime: Date.now(), frameCount: 0, forceHistory: [] });
    get().addLog('success', `扫描启动 [${sid}]`);
  },

  stopScan: () => {
    const sid = get().sessionId;
    set({ scanState: 'idle', executionState: 'RETREATING', startTime: null });
    get().addLog('info', `扫描停止 [${sid}]，共 ${get().frameCount} 帧`);
  },

  triggerHalt: () => {
    set({ scanState: 'halted', executionState: 'ESTOP' });
    get().addLog('error', '⚠ 紧急制动已激活 — 硬件锁定');
  },

  resetHalt: () => {
    set({ scanState: 'idle', executionState: 'AUTO_READY' });
    get().addLog('warn', '制动已解除 — 系统恢复待机');
  },

  addLog: (level, msg) => {
    set(s => ({
      logs: [...s.logs.slice(-200), { time: timeStr(), level, msg }]
    }));
  },

  pushAlarm: (alarm) => {
    set((s) => ({
      alarms: [...s.alarms.slice(-99), alarm],
    }));
  },

  setSessionReport: (report) => set({ sessionReport: report }),
  setReplayIndex: (replay) => set({ replayIndex: replay }),

  pushForce: (v) => {
    if (get().scanState !== 'scanning') return;
    set(s => ({
      forceHistory: [...s.forceHistory.slice(-3000), { t: Date.now(), v }]
    }));
  },

  incrementFrame: () => set(s => ({ frameCount: s.frameCount + 1 })),

  syncCoreState: (executionState, sessionId) => set((state) => {
    let scanState = state.scanState;
    if (executionState === 'SCANNING') {
      scanState = 'scanning';
    } else if (executionState === 'PAUSED_HOLD') {
      scanState = 'paused';
    } else if (executionState === 'ESTOP') {
      scanState = 'halted';
    } else {
      scanState = 'idle';
    }
    return {
      executionState,
      scanState,
      sessionId: sessionId || state.sessionId,
      startTime: scanState === 'scanning' ? state.startTime || Date.now() : state.startTime,
    };
  }),

  exportCSV: () => {
    const rows = get().forceHistory;
    if (rows.length === 0) return;
    const csv = 'timestamp_ms,force_N\n' + rows.map(r => `${r.t},${r.v.toFixed(4)}`).join('\n');
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
