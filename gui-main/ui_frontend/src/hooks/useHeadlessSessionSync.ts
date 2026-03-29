import { startTransition, useEffect } from 'react';
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
  fetchCurrentSelectedExecutionRationale,
  fetchCurrentReleaseGateDecision,
  fetchCurrentCommandPolicySnapshot,
  fetchCurrentContractKernelDiff,
  fetchCurrentScanProtocol,
  fetchCurrentSession,
  fetchCurrentTrends,
  fetchHealth,
  fetchProtocolSchema,
  type CurrentSessionEnvelope,
  type DeviceReadinessEnvelope,
  type HealthEnvelope,
  type ProtocolSchema,
} from '../api/client';
import { useSessionStore } from '../store/sessionStore';
import type { Workspace } from '../store/uiStore';

interface SyncOptions {
  workspace: Workspace;
  setProtocolSchema: (value: ProtocolSchema | null) => void;
  setHealth: (value: HealthEnvelope | null) => void;
  setCurrentSession: (value: CurrentSessionEnvelope | null) => void;
  setReadiness: (value: DeviceReadinessEnvelope | null) => void;
}

export function useHeadlessSessionSync({ workspace, setProtocolSchema, setHealth, setCurrentSession, setReadiness }: SyncOptions) {
  const productUpdateTick = useSessionStore((s) => s.productUpdateTick);
  const pendingProductTopics = useSessionStore((s) => s.pendingProductTopics);

  useEffect(() => {
    let cancelled = false;
    fetchProtocolSchema()
      .then((schema) => {
        if (!cancelled) startTransition(() => setProtocolSchema(schema));
      })
      .catch((error) => useSessionStore.getState().addLog('warn', `schema 加载失败: ${error instanceof Error ? error.message : 'unknown'}`));
    return () => {
      cancelled = true;
    };
  }, [setProtocolSchema]);

  useEffect(() => {
    let cancelled = false;
    const sync = async () => {
      const store = useSessionStore.getState();
      try {
        const [healthPayload, sessionPayload] = await Promise.all([fetchHealth(), fetchCurrentSession().catch(() => null)]);
        if (cancelled) return;
        startTransition(() => {
          setHealth(healthPayload);
          setCurrentSession(sessionPayload);
        });
        store.syncCoreState(healthPayload.execution_state, sessionPayload?.session_id ?? null, sessionPayload?.session_started_at ?? null);
        if (!sessionPayload) {
          startTransition(() => {
            store.setSessionReport(null);
            store.setReplayIndex(null);
            store.setQualityTimeline(null);
            store.setFrameSync(null);
            store.setArtifacts(null);
            store.setCompare(null);
            store.setTrends(null);
            store.setDiagnostics(null);
            store.setSelectedExecutionRationale(null);
            store.setReleaseGateDecision(null);
            store.setCommandPolicySnapshot(null);
            store.setContractKernelDiff(null);
            store.setCommandTrace(null);
            store.setAssessment(null);
            store.setProfile(null);
            store.setPatientRegistration(null);
            store.setScanProtocol(null);
            store.setQaPack(null);
            store.setAnnotations([]);
            setReadiness(null);
            store.setAlarmTimeline(null);
          });
          return;
        }

        const changedTopics = store.consumeProductTopics();
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
          shouldFetch('selected_execution_rationale_updated') && sessionPayload.selected_execution_rationale_available ? fetchCurrentSelectedExecutionRationale().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('release_gate_updated') && sessionPayload.release_gate_available ? fetchCurrentReleaseGateDecision().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('command_policy_snapshot_updated') && sessionPayload.command_policy_snapshot_available ? fetchCurrentCommandPolicySnapshot().catch(() => null) : Promise.resolve(undefined),
          shouldFetch('contract_kernel_diff_updated') && sessionPayload.contract_kernel_diff_available ? fetchCurrentContractKernelDiff().catch(() => null) : Promise.resolve(undefined),
        ]);
        if (cancelled) return;
        const [report, replay, quality, frameSyncPayload, alarmPayload, artifactsPayload, comparePayload, trendsPayload, diagnosticsPayload, annotationsPayload, readinessPayload, profilePayload, registrationPayload, scanProtocolPayload, qaPayload, commandTracePayload, assessmentPayload, selectedExecutionPayload, releaseGatePayload, commandPolicySnapshotPayload, contractKernelDiffPayload] = promises;
        startTransition(() => {
          if (report !== undefined) store.setSessionReport(report ?? null);
          if (replay !== undefined) store.setReplayIndex(replay ?? null);
          if (quality !== undefined) store.setQualityTimeline(quality ?? null);
          if (frameSyncPayload !== undefined) store.setFrameSync(frameSyncPayload ?? null);
          if (alarmPayload !== undefined) store.setAlarmTimeline(alarmPayload ?? null);
          if (artifactsPayload !== undefined) store.setArtifacts(artifactsPayload ?? null);
          if (comparePayload !== undefined) store.setCompare(comparePayload ?? null);
          if (trendsPayload !== undefined) store.setTrends(trendsPayload ?? null);
          if (diagnosticsPayload !== undefined) store.setDiagnostics(diagnosticsPayload ?? null);
          if (selectedExecutionPayload !== undefined) store.setSelectedExecutionRationale(selectedExecutionPayload ?? null);
          if (releaseGatePayload !== undefined) store.setReleaseGateDecision(releaseGatePayload ?? null);
          if (commandPolicySnapshotPayload !== undefined) store.setCommandPolicySnapshot(commandPolicySnapshotPayload ?? null);
          if (contractKernelDiffPayload !== undefined) store.setContractKernelDiff(contractKernelDiffPayload ?? null);
          if (annotationsPayload !== undefined) store.setAnnotations(annotationsPayload?.annotations ?? []);
          if (readinessPayload !== undefined) setReadiness(readinessPayload ?? null);
          if (profilePayload !== undefined) store.setProfile(profilePayload ?? null);
          if (registrationPayload !== undefined) store.setPatientRegistration(registrationPayload ?? null);
          if (scanProtocolPayload !== undefined) store.setScanProtocol(scanProtocolPayload ?? null);
          if (qaPayload !== undefined) store.setQaPack(qaPayload ?? null);
          if (commandTracePayload !== undefined) store.setCommandTrace(commandTracePayload ?? null);
          if (assessmentPayload !== undefined) store.setAssessment(assessmentPayload ?? null);
        });
      } catch (error) {
        useSessionStore.getState().addLog('warn', `headless 健康检查失败: ${error instanceof Error ? error.message : 'unknown'}`);
      }
    };
    void sync();
    const interval = window.setInterval(sync, workspace === 'researcher' ? 3500 : 2000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [workspace, productUpdateTick, pendingProductTopics, setCurrentSession, setHealth, setReadiness]);
}
