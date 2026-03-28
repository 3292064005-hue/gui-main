import { useCallback, useEffect, useRef } from 'react';
import { parseTelemetryMessage } from '../api/client';
import { wsUrl } from '../api/config';
import { useTelemetryStore } from '../store/telemetryStore';
import { useSessionStore } from '../store/sessionStore';

const TELEMETRY_WS_URL = wsUrl('/ws/telemetry');
const MAX_BACKOFF = 8000;
const EMPTY_JOINTS = [0, 0, 0, 0, 0, 0, 0];

function asNumberArray(value: unknown, expectedLength: number): number[] {
  if (!Array.isArray(value)) {
    return EMPTY_JOINTS.slice(0, expectedLength);
  }
  return value.slice(0, expectedLength).map((item) => (typeof item === 'number' ? item : Number(item) || 0));
}

export function useTelemetrySocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) {
      return;
    }

    const ws = new WebSocket(TELEMETRY_WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      backoffRef.current = 1000;
      useTelemetryStore.getState().setConnected(true);
      useSessionStore.getState().addLog('success', '遥测通道已连接 (Headless v1)');
    };

    ws.onclose = () => {
      useTelemetryStore.getState().setConnected(false);
      if (!mountedRef.current) {
        return;
      }
      const jitter = Math.random() * 500;
      const delay = Math.min(backoffRef.current + jitter, MAX_BACKOFF);
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF);
      useSessionStore.getState().addLog('warn', `遥测断开，${(delay / 1000).toFixed(1)}秒后重连...`);
      window.setTimeout(connect, delay);
    };

    ws.onerror = () => {
      useSessionStore.getState().addLog('error', 'WebSocket 连接错误');
    };

    ws.onmessage = (event) => {
      const message = parseTelemetryMessage(event.data);
      if (!message) {
        return;
      }

      const tsMs = Math.max(0, Math.round(message.ts_ns / 1_000_000));
      useTelemetryStore.getState().setLatency(Math.max(0, Date.now() - tsMs));

      if (message.topic === 'core_state') {
        const executionState =
          typeof message.data.execution_state === 'string' ? message.data.execution_state : 'BOOT';
        const sessionId =
          typeof message.data.session_id === 'string' && message.data.session_id
            ? message.data.session_id
            : null;
        useSessionStore.getState().syncCoreState(executionState, sessionId);
        return;
      }

      if (message.topic === 'robot_state') {
        const cartForce = asNumberArray(message.data.cart_force, 6);
        const joints = asNumberArray(message.data.joint_pos, 7);
        useTelemetryStore.getState().mergeTelemetry({
          timestamp: tsMs,
          force: cartForce[2] ?? 0,
          joints,
        });
        return;
      }

      if (message.topic === 'contact_state') {
        const force =
          typeof message.data.pressure_current === 'number' ? message.data.pressure_current : undefined;
        if (useSessionStore.getState().scanState === 'scanning') {
          useSessionStore.getState().pushForce(force ?? 0);
        }
        return;
      }

      if (message.topic === 'scan_progress' && useSessionStore.getState().scanState === 'scanning') {
        useSessionStore.getState().incrementFrame();
        return;
      }

      if (message.topic === 'safety_status') {
        const safeToScan = message.data.safe_to_scan === true;
        useTelemetryStore.getState().mergeTelemetry({
          timestamp: tsMs,
          safety: safeToScan ? 0 : 1,
        });
        return;
      }

      if (message.topic === 'alarm_event') {
        useSessionStore.getState().pushAlarm({
          tsNs: message.ts_ns,
          severity: typeof message.data.severity === 'string' ? message.data.severity : 'WARN',
          source: typeof message.data.source === 'string' ? message.data.source : 'runtime',
          message: typeof message.data.message === 'string' ? message.data.message : '未知告警',
          workflowStep: typeof message.data.workflow_step === 'string' ? message.data.workflow_step : '',
          requestId: typeof message.data.request_id === 'string' ? message.data.request_id : '',
          autoAction: typeof message.data.auto_action === 'string' ? message.data.auto_action : '',
        });
        useSessionStore.getState().addLog(
          'warn',
          `[告警] ${typeof message.data.source === 'string' ? message.data.source : 'runtime'}: ${
            typeof message.data.message === 'string' ? message.data.message : '未知告警'
          }`,
        );
      }
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
    };
  }, [connect]);
}
