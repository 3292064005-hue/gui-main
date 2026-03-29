import { useCallback, useEffect, useRef } from 'react';
import { buildTelemetryWsUrl, parseTelemetryMessage } from '../api/client';
import { useTelemetryStore } from '../store/telemetryStore';
import { useSessionStore } from '../store/sessionStore';
import type { Workspace } from '../store/uiStore';

const MAX_BACKOFF = 8000;
const EMPTY_JOINTS = [0, 0, 0, 0, 0, 0];

const TOPICS_BY_WORKSPACE: Record<Workspace, string[]> = {
  operator: [
    'core_state',
    'robot_state',
    'contact_state',
    'scan_progress',
    'safety_status',
    'alarm_event',
    'session_product_update',
    'readiness_updated',
    'registration_updated',
    'scan_protocol_updated',
    'quality_updated',
    'alarms_updated',
  ],
  researcher: [
    'core_state',
    'robot_state',
    'contact_state',
    'alarm_event',
    'session_product_update',
    'compare_updated',
    'trends_updated',
    'diagnostics_updated',
    'artifact_ready',
    'assessment_updated',
    'command_trace_updated',
    'replay_updated',
    'frame_sync_updated',
    'qa_pack_updated',
    'annotations_updated',
    'event_log_index_updated',
    'recovery_timeline_updated',
  ],
  qa: [
    'session_product_update',
    'artifact_ready',
    'diagnostics_updated',
    'event_log_index_updated',
    'recovery_timeline_updated',
    'resume_decision_updated',
    'incidents_updated',
  ],
  review: [
    'session_product_update',
    'artifact_ready',
    'report_updated',
    'replay_updated',
    'annotations_updated',
    'event_log_index_updated',
    'recovery_timeline_updated',
  ],
};

function asNumberArray(value: unknown, expectedLength: number): number[] {
  if (!Array.isArray(value)) return EMPTY_JOINTS.slice(0, expectedLength);
  return value.slice(0, expectedLength).map((item) => (typeof item === 'number' ? item : Number(item) || 0));
}

export function useTelemetrySocket(workspace: Workspace) {
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const mountedRef = useRef(true);
  const urlRef = useRef('');

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    const nextUrl = buildTelemetryWsUrl(TOPICS_BY_WORKSPACE[workspace]);
    urlRef.current = nextUrl;
    const ws = new WebSocket(nextUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      backoffRef.current = 1000;
      useTelemetryStore.getState().setConnected(true);
      useSessionStore.getState().addLog('success', `遥测通道已连接 (${workspace})`);
    };

    ws.onclose = () => {
      useTelemetryStore.getState().setConnected(false);
      if (!mountedRef.current) return;
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
      if (!message) return;

      const tsMs = Math.max(0, Math.round(message.ts_ns / 1_000_000));
      useTelemetryStore.getState().setLatency(Math.max(0, Date.now() - tsMs));

      if (message.topic === 'session_product_update') {
        const changedTopics = Array.isArray(message.data.changed_topics)
          ? message.data.changed_topics.filter((topic): topic is string => typeof topic === 'string')
          : [];
        useSessionStore.getState().markProductUpdate(changedTopics);
        return;
      }

      if (message.topic.endsWith('_updated') || message.topic === 'artifact_ready') {
        const changedTopics = Array.isArray(message.data.changed_topics)
          ? message.data.changed_topics.filter((topic): topic is string => typeof topic === 'string')
          : [message.topic];
        useSessionStore.getState().markProductUpdate(changedTopics);
        return;
      }

      if (message.topic === 'core_state') {
        const executionState = typeof message.data.execution_state === 'string' ? message.data.execution_state : 'BOOT';
        const sessionId = typeof message.data.session_id === 'string' && message.data.session_id ? message.data.session_id : null;
        useSessionStore.getState().syncCoreState(executionState, sessionId);
        return;
      }

      if (message.topic === 'robot_state') {
        const cartForce = asNumberArray(message.data.cart_force, 6);
        const joints = asNumberArray(message.data.joint_pos, 6);
        useTelemetryStore.getState().mergeTelemetry({ timestamp: tsMs, force: cartForce[2] ?? 0, joints });
        return;
      }

      if (message.topic === 'contact_state') {
        const force = typeof message.data.pressure_current === 'number' ? message.data.pressure_current : undefined;
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
        useTelemetryStore.getState().mergeTelemetry({ timestamp: tsMs, safety: safeToScan ? 0 : 1 });
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
          `[告警] ${typeof message.data.source === 'string' ? message.data.source : 'runtime'}: ${typeof message.data.message === 'string' ? message.data.message : '未知告警'}`,
        );
      }
    };
  }, [workspace]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      wsRef.current?.close();
    };
  }, [connect]);
}
