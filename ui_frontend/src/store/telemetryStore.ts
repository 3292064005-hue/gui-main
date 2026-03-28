import { create } from 'zustand';

interface TelemetryState {
  connected: boolean;
  timestamp: number;
  force: number;
  safety: number; // 0 = OK, 1 = HALT
  joints: number[]; // 7-DOF
  latencyMs: number;
  telemetryStale: boolean;
  fps: number;
  // Internal FPS tracking
  _frameCount: number;
  _lastFpsTime: number;

  setConnected: (v: boolean) => void;
  pushTelemetry: (ts: number, force: number, safety: number, joints: number[]) => void;
  mergeTelemetry: (update: Partial<Pick<TelemetryState, 'timestamp' | 'force' | 'safety' | 'joints'>>) => void;
  setLatency: (ms: number) => void;
  setTelemetryStale: (stale: boolean) => void;
  reset: () => void;
}

export const useTelemetryStore = create<TelemetryState>((set, get) => ({
  connected: false,
  timestamp: 0,
  force: 0,
  safety: 0,
  joints: [0, 0, 0, 0, 0, 0, 0],
  latencyMs: 0,
  telemetryStale: false,
  fps: 0,
  _frameCount: 0,
  _lastFpsTime: Date.now(),

  setConnected: (v) => set({ connected: v }),

  mergeTelemetry: (update) => {
    const state = get();
    const ts = update.timestamp ?? state.timestamp;
    const force = update.force ?? state.force;
    const safety = update.safety ?? state.safety;
    const joints = update.joints ?? state.joints;
    const now = Date.now();
    let newFps = state.fps;
    let newCount = state._frameCount + 1;
    let lastTime = state._lastFpsTime;

    // Calculate FPS every second
    if (now - lastTime >= 1000) {
      newFps = newCount;
      newCount = 0;
      lastTime = now;
    }

    set({
      timestamp: ts,
      force,
      safety,
      joints,
      fps: newFps,
      _frameCount: newCount,
      _lastFpsTime: lastTime,
    });
  },

  pushTelemetry: (ts, force, safety, joints) => {
    get().mergeTelemetry({ timestamp: ts, force, safety, joints });
  },

  setLatency: (ms) => set({ latencyMs: ms }),
  setTelemetryStale: (stale) => set({ telemetryStale: stale }),

  reset: () => set({
    force: 0, safety: 0, joints: [0, 0, 0, 0, 0, 0, 0], fps: 0, _frameCount: 0, telemetryStale: false
  }),
}));
