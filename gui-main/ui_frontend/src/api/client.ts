import { apiUrl, wsUrl } from './config';

export type WorkspaceRole = 'operator' | 'researcher' | 'reviewer' | 'service' | 'admin' | 'read_only';

export interface ReplyEnvelope {
  ok: boolean;
  message: string;
  request_id?: string;
  data: Record<string, unknown>;
  protocol_version: number;
}

export interface ProtocolSchema {
  api_version: string;
  protocol_version: number;
  commands: Record<string, Record<string, unknown>>;
  telemetry_topics: Record<string, Record<string, unknown>>;
  contract_schemas?: string[];
  force_control: {
    max_z_force_n: number;
    warning_z_force_n: number;
    max_xy_force_n: number;
    desired_contact_force_n: number;
    emergency_retract_mm: number;
    force_filter_cutoff_hz: number;
    sensor_timeout_ms: number;
    stale_telemetry_ms: number;
    force_settle_window_ms: number;
    resume_force_band_n: number;
  };
}

export interface TelemetryMessage {
  topic: string;
  ts_ns: number;
  data: Record<string, unknown>;
}

export interface HealthEnvelope {
  backend_mode: string;
  adapter_running: boolean;
  protocol_version: number;
  topics: string[];
  latest_telemetry_age_ms: number | null;
  telemetry_stale: boolean;
  stale_threshold_ms: number;
  recovery_state: string;
  force_sensor_provider: string;
  robot_model?: string;
  session_locked: boolean;
  build_id: string;
  software_version: string;
  execution_state: string;
  powered: boolean;
  read_only_mode: boolean;
}

export interface ArtifactDescriptor {
  artifact_type: string;
  path: string;
  mime_type: string;
  producer: string;
  schema?: string;
  schema_version: string;
  artifact_id: string;
  ready: boolean;
  size_bytes: number;
  checksum?: string;
  created_at?: string;
  summary: string;
  source_stage?: string;
  dependencies?: string[];
}

export interface DeviceReadinessEnvelope {
  generated_at?: string;
  robot_ready: boolean;
  camera_ready: boolean;
  ultrasound_ready: boolean;
  force_provider_ready: boolean;
  storage_ready: boolean;
  config_valid: boolean;
  protocol_match: boolean;
  software_version?: string;
  build_id?: string;
  time_sync_ok: boolean;
  ready_to_lock?: boolean;
  network_link_ok?: boolean;
  single_control_source_ok?: boolean;
  rt_control_ready?: boolean;
  control_authority?: string;
}

export interface CurrentSessionEnvelope {
  session_id: string;
  session_dir: string;
  session_started_at?: string;
  artifacts: Record<string, string>;
  artifact_registry?: Record<string, ArtifactDescriptor>;
  readiness_available?: boolean;
  profile_available?: boolean;
  patient_registration_available?: boolean;
  scan_protocol_available?: boolean;
  report_available: boolean;
  replay_available: boolean;
  qa_pack_available?: boolean;
  compare_available?: boolean;
  trends_available?: boolean;
  diagnostics_available?: boolean;
  frame_sync_available?: boolean;
  command_trace_available?: boolean;
  assessment_available?: boolean;
  command_policy_snapshot_available?: boolean;
  contract_kernel_diff_available?: boolean;
  selected_execution_rationale_available?: boolean;
  release_gate_available?: boolean;
  contact_available?: boolean;
  recovery_available?: boolean;
  integrity_available?: boolean;
  operator_incidents_available?: boolean;
  status: Record<string, unknown>;
}

export interface SessionReportEnvelope {
  session_id: string;
  experiment_id?: string;
  session_overview?: Record<string, unknown>;
  workflow_trace?: Record<string, unknown>;
  quality_summary?: Record<string, unknown>;
  safety_summary?: Record<string, unknown>;
  operator_actions?: Record<string, unknown>;
  devices?: Record<string, unknown>;
  outputs?: Record<string, ArtifactDescriptor>;
  replay?: Record<string, unknown>;
  algorithm_versions?: Record<string, unknown>;
  open_issues?: string[];
}

export interface ReplayIndexEnvelope {
  session_id: string;
  channels?: string[];
  streams?: Record<string, unknown>;
  timeline?: Array<Record<string, unknown>>;
  alarm_segments?: Array<Record<string, unknown>>;
  quality_segments?: Array<Record<string, unknown>>;
  annotation_segments?: Array<Record<string, unknown>>;
  notable_events?: Array<Record<string, unknown>>;
}

export interface FrameSyncEnvelope {
  session_id: string;
  rows: Array<Record<string, unknown>>;
  summary?: Record<string, unknown>;
}

export interface AlarmTimelineEnvelope {
  session_id: string;
  events: Array<Record<string, unknown>>;
  summary?: Record<string, unknown>;
}

export interface QualityTimelineEnvelope {
  session_id: string;
  points: Array<Record<string, unknown>>;
  summary?: Record<string, unknown>;
}

export interface ArtifactsEnvelope {
  session_id: string;
  artifacts: Record<string, string>;
  artifact_registry: Record<string, ArtifactDescriptor>;
  processing_steps: Array<Record<string, unknown>>;
  algorithm_registry?: Record<string, { plugin_id: string; plugin_version: string }>;
  warnings?: string[];
}

export interface SessionCompareEnvelope {
  session_id: string;
  baseline_session_id?: string;
  current: Record<string, number | string>;
  baseline?: Record<string, number | string>;
  fleet_summary: Record<string, number | string>;
  delta_vs_baseline?: Record<string, number | string>;
}

export interface SessionTrendsEnvelope {
  session_id: string;
  history_window: number;
  history_count: number;
  current: Record<string, number | string>;
  history: Array<Record<string, number | string>>;
  trends: Record<string, number | string>;
  fleet_summary: Record<string, number | string>;
}

export interface DiagnosticsPackEnvelope {
  session_id: string;
  health_snapshot: Record<string, unknown>;
  manifest_excerpt?: Record<string, unknown>;
  last_commands: Array<Record<string, unknown>>;
  last_alarms: Array<Record<string, unknown>>;
  annotation_tail?: Array<Record<string, unknown>>;
  telemetry_summary?: Record<string, unknown>;
  command_digest?: Record<string, unknown>;
  alarm_digest?: Record<string, unknown>;
  quality_digest?: Record<string, unknown>;
  artifact_digest?: Record<string, unknown>;
  recovery_snapshot?: Record<string, unknown>;
  environment?: Record<string, unknown>;
  versioning?: Record<string, unknown>;
  recommendations?: string[];
  schemas?: Record<string, string>;
  summary?: Record<string, number | string>;
}


export interface SelectedExecutionRationaleEnvelope {
  session_id?: string;
  selected_candidate_id?: string;
  selected_plan_id?: string;
  selection_basis?: Record<string, unknown>;
  tradeoff_summary?: Record<string, unknown>;
  selected_score?: Record<string, unknown>;
  ranking_snapshot?: Array<Record<string, unknown>>;
  rejected_candidate_reasons?: string[];
}

export interface ReleaseGateDecisionEnvelope {
  session_id?: string;
  release_allowed: boolean;
  blocking_reasons?: string[];
  warning_reasons?: string[];
  required_remediations?: string[];
  checks?: Record<string, boolean>;
}

export interface AnnotationEntry {
  kind?: string;
  message?: string;
  ts_ns?: number;
  segment_id?: number;
  severity?: string;
  tags?: string[];
}

export interface AnnotationsEnvelope {
  session_id: string;
  annotations: AnnotationEntry[];
}

export interface XMateProfileEnvelope {
  robot_model?: string;
  sdk_robot_class?: string;
  axis_count?: number;
  tcp_frame_matrix?: number[];
  fc_frame_type?: string;
  desired_wrench_n?: number[];
  cartesian_impedance?: number[];
  rt_network_tolerance_percent?: number;
  [key: string]: unknown;
}

export interface PatientRegistrationEnvelope {
  session_id?: string;
  source?: string;
  registration_quality?: number;
  patient_frame?: Record<string, unknown>;
  scan_corridor?: Record<string, unknown>;
  landmarks?: Array<Record<string, unknown>>;
  body_surface?: Record<string, unknown>;
  camera_observations?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ScanProtocolEnvelope {
  protocol_id?: string;
  clinical_control_modes?: Record<string, unknown>;
  contact_control?: Record<string, unknown>;
  path_policy?: Record<string, unknown>;
  registration_contract?: Record<string, unknown>;
  rt_parameters?: Record<string, unknown>;
  safety_contract?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface QaPackEnvelope {
  session_dir: string;
  manifest: Record<string, unknown>;
  report: SessionReportEnvelope;
  replay: ReplayIndexEnvelope;
  quality: QualityTimelineEnvelope;
  alarms: AlarmTimelineEnvelope;
  frame_sync?: Record<string, unknown>;
  compare?: SessionCompareEnvelope;
  trends?: SessionTrendsEnvelope;
  diagnostics?: DiagnosticsPackEnvelope;
  annotations?: AnnotationEntry[];
  schemas: Record<string, Record<string, unknown>>;
}

export interface CommandTraceEntry {
  command?: string;
  workflow_step?: string;
  auto_action?: string;
  payload_summary?: Record<string, unknown> | string;
  reply?: Record<string, unknown>;
  ts_ns?: number;
}

export interface CommandTraceEnvelope {
  session_id: string;
  entries: CommandTraceEntry[];
  summary?: Record<string, number | string>;
}

export interface AssessmentEnvelope {
  session_id: string;
  robot_model?: string;
  summary?: Record<string, number | string>;
  curve_candidate?: Record<string, unknown>;
  cobb_candidate_deg?: number | null;
  confidence?: number;
  requires_manual_review?: boolean;
  landmark_candidates?: Array<Record<string, unknown>>;
  evidence_frames?: Array<Record<string, unknown>>;
  open_issues?: string[];
}

export interface ContactEnvelope {
  session_id: string;
  execution_state: string;
  contact_mode: string;
  contact_confidence: number;
  pressure_current: number;
  recommended_action: string;
  contact_stable: boolean;
  active_segment: number;
}

export interface RecoveryEnvelope {
  session_id: string;
  execution_state: string;
  recovery_state: string;
  recovery_reason: string;
  last_recovery_action: string;
  active_interlocks: string[];
}

export interface SessionIntegrityEnvelope {
  session_id: string;
  session_dir: string;
  artifacts: Array<Record<string, unknown>>;
  summary: Record<string, number | boolean>;
  manifest_consistency: Record<string, unknown>;
  missing_artifacts: string[];
  checksum_mismatch_artifacts: string[];
  warnings: string[];
}

export interface OperatorIncidentsEnvelope {
  session_id: string;
  count: number;
  incidents: Array<Record<string, unknown>>;
}

function readErrorDetail(payload: unknown): string {
  if (!payload || typeof payload !== 'object') return 'adapter request failed';
  const detail = (payload as { detail?: unknown }).detail;
  return typeof detail === 'string' && detail ? detail : 'adapter request failed';
}

export async function postCommand(
  command: string,
  payload: Record<string, unknown> = {},
  role: WorkspaceRole = 'operator',
): Promise<ReplyEnvelope> {
  const response = await fetch(apiUrl(`/api/v1/commands/${command}`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Spine-Role': role,
    },
    body: JSON.stringify(payload),
  });
  const body = (await response.json()) as unknown;
  if (!response.ok) throw new Error(readErrorDetail(body));
  return body as ReplyEnvelope;
}

export async function fetchProtocolSchema(): Promise<ProtocolSchema> { return fetchJson('/api/v1/schema'); }
export async function fetchHealth(): Promise<HealthEnvelope> { return fetchJson('/api/v1/health'); }
export async function fetchCurrentSession(): Promise<CurrentSessionEnvelope> { return fetchJson('/api/v1/sessions/current'); }
export async function fetchCurrentReport(): Promise<SessionReportEnvelope> { return fetchJson('/api/v1/sessions/current/report'); }
export async function fetchCurrentReplay(): Promise<ReplayIndexEnvelope> { return fetchJson('/api/v1/sessions/current/replay'); }
export async function fetchCurrentQuality(): Promise<QualityTimelineEnvelope> { return fetchJson('/api/v1/sessions/current/quality'); }
export async function fetchCurrentFrameSync(): Promise<FrameSyncEnvelope> { return fetchJson('/api/v1/sessions/current/frame-sync'); }
export async function fetchCurrentAlarms(): Promise<AlarmTimelineEnvelope> { return fetchJson('/api/v1/sessions/current/alarms'); }
export async function fetchCurrentArtifacts(): Promise<ArtifactsEnvelope> { return fetchJson('/api/v1/sessions/current/artifacts'); }
export async function fetchCurrentCompare(): Promise<SessionCompareEnvelope> { return fetchJson('/api/v1/sessions/current/compare'); }
export async function fetchCurrentTrends(): Promise<SessionTrendsEnvelope> { return fetchJson('/api/v1/sessions/current/trends'); }
export async function fetchCurrentDiagnostics(): Promise<DiagnosticsPackEnvelope> { return fetchJson('/api/v1/sessions/current/diagnostics'); }
export async function fetchCurrentAnnotations(): Promise<AnnotationsEnvelope> { return fetchJson('/api/v1/sessions/current/annotations'); }
export async function fetchCurrentReadiness(): Promise<DeviceReadinessEnvelope> { return fetchJson('/api/v1/sessions/current/readiness'); }
export async function fetchCurrentProfile(): Promise<XMateProfileEnvelope> { return fetchJson('/api/v1/sessions/current/profile'); }
export async function fetchCurrentPatientRegistration(): Promise<PatientRegistrationEnvelope> { return fetchJson('/api/v1/sessions/current/patient-registration'); }
export async function fetchCurrentScanProtocol(): Promise<ScanProtocolEnvelope> { return fetchJson('/api/v1/sessions/current/scan-protocol'); }
export async function fetchCurrentQaPack(): Promise<QaPackEnvelope> { return fetchJson('/api/v1/sessions/current/qa-pack'); }
export async function fetchCurrentCommandTrace(): Promise<CommandTraceEnvelope> { return fetchJson('/api/v1/sessions/current/command-trace'); }
export async function fetchCurrentAssessment(): Promise<AssessmentEnvelope> { return fetchJson('/api/v1/sessions/current/assessment'); }
export async function fetchCurrentContact(): Promise<ContactEnvelope> { return fetchJson('/api/v1/sessions/current/contact'); }
export async function fetchCurrentRecovery(): Promise<RecoveryEnvelope> { return fetchJson('/api/v1/sessions/current/recovery'); }
export async function fetchCurrentIntegrity(): Promise<SessionIntegrityEnvelope> { return fetchJson('/api/v1/sessions/current/integrity'); }
export async function fetchCurrentOperatorIncidents(): Promise<OperatorIncidentsEnvelope> { return fetchJson('/api/v1/sessions/current/operator-incidents'); }

export function buildTelemetryWsUrl(topics?: string[]): string {
  const base = wsUrl('/ws/telemetry');
  if (!topics || topics.length === 0) return base;
  const query = new URLSearchParams({ topics: topics.join(',') });
  return `${base}?${query.toString()}`;
}

export function parseTelemetryMessage(raw: unknown): TelemetryMessage | null {
  const candidate = typeof raw === 'string' ? safeParse(raw) : raw;
  if (!candidate || typeof candidate !== 'object') return null;
  const parsed = candidate as Partial<TelemetryMessage>;
  if (typeof parsed.topic !== 'string' || typeof parsed.ts_ns !== 'number' || typeof parsed.data !== 'object' || parsed.data === null) {
    return null;
  }
  return parsed as TelemetryMessage;
}

function safeParse(raw: string): unknown {
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return null;
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(apiUrl(path));
  const body = (await response.json()) as unknown;
  if (!response.ok) throw new Error(readErrorDetail(body));
  return body as T;
}


export interface SessionIncidentsEnvelope {
  session_id: string;
  summary: Record<string, unknown>;
  incidents: Array<Record<string, unknown>>;
}

export interface ResumeDecisionEnvelope {
  session_id: string;
  resume_allowed: boolean;
  mode: string;
  blocking_reasons: string[];
  resume_from?: Record<string, unknown>;
  recommended_patch_segments?: number[];
}

export interface RoleCatalogEnvelope {
  roles: Record<string, Record<string, unknown>>;
  command_groups?: Record<string, string[]>;
}

export interface EventLogIndexEnvelope {
  session_id: string;
  events: Array<Record<string, unknown>>;
  summary: Record<string, unknown>;
  continuity_gaps?: Array<Record<string, unknown>>;
}

export interface RecoveryTimelineEnvelope {
  session_id: string;
  timeline: Array<Record<string, unknown>>;
  summary?: Record<string, unknown>;
}

export interface ResumeAttemptsEnvelope {
  session_id: string;
  summary: Record<string, unknown>;
  attempts: Array<Record<string, unknown>>;
}

export interface ContractConsistencyEnvelope {
  session_id: string;
  summary: Record<string, unknown>;
  version_alignment?: Record<string, unknown>;
  hash_alignment?: Record<string, unknown>;
  required_artifacts?: Array<Record<string, unknown>>;
  mismatches?: Array<Record<string, unknown>>;
  warnings?: string[];
}

export interface ReleaseEvidenceEnvelope {
  session_id: string;
  release_candidate: boolean;
  release_readiness?: Record<string, unknown>;
  version_lock?: Record<string, unknown>;
  diagnostics_summary?: Record<string, unknown>;
  integrity_summary?: Record<string, unknown>;
  contract_summary?: Record<string, unknown>;
  evidence_index?: Array<Record<string, unknown>>;
  open_gaps?: string[];
}

export interface CommandPolicyCatalogEnvelope {
  generated_at?: string;
  schema?: string;
  known_states?: string[];
  policies: Array<Record<string, unknown>>;
}



export interface ContractKernelDiffEnvelope {
  session_id?: string;
  service_version?: string;
  summary?: { consistent?: boolean; diff_count?: number; checked_object_count?: number };
  checks?: Record<string, boolean>;
  diffs?: Array<Record<string, unknown>>;
}

export interface CommandPolicySnapshotEnvelope {
  session_id: string;
  policy_version?: string;
  execution_state?: string;
  contact_state?: string;
  plan_state?: string;
  resume_mode?: string;
  role?: string;
  read_only?: boolean;
  decision_count?: number;
  decisions?: Record<string, Record<string, unknown>>;
  plan_hash?: string;
}
export interface EventDeliverySummaryEnvelope {
  session_id: string;
  summary: Record<string, unknown>;
  continuity_gaps?: Array<Record<string, unknown>>;
  delivery_classes?: Record<string, number>;
  resume_outcome_summary?: Record<string, unknown>;
  contract_consistency_summary?: Record<string, unknown>;
}

export interface EventDeliveryAuditEnvelope {
  generated_at_ns?: number;
  delivery_rules?: Record<string, Record<string, unknown>>;
  pending_acks?: Array<Record<string, unknown>>;
  dead_letters?: Record<string, unknown>;
  subscriber_health?: Record<string, unknown>;
  replay?: Record<string, unknown>;
}

export interface DeadLetterEnvelope {
  entries: Array<Record<string, unknown>>;
  summary: Record<string, unknown>;
}

export interface ResumeAttemptOutcomesEnvelope {
  session_id: string;
  summary: Record<string, unknown>;
  outcomes: Array<Record<string, unknown>>;
}

export interface EventBusStatsEnvelope {
  published_events: number;
  subscriber_count: number;
  pending_ack_count?: number;
  delivery_failures?: number;
  delivery_retries?: number;
  slow_subscribers?: number;
  max_queue_depth?: number;
  published_by_topic?: Record<string, number>;
  published_by_delivery?: Record<string, number>;
  published_by_category?: Record<string, number>;
  replay?: Record<string, unknown>;
}

export interface EventReplayEnvelope {
  session_id?: string;
  events: Array<Record<string, unknown>>;
  summary?: Record<string, unknown>;
}

export async function fetchCurrentIncidents(): Promise<SessionIncidentsEnvelope> {
  return fetchJson<SessionIncidentsEnvelope>('/api/v1/sessions/current/incidents');
}

export async function fetchCurrentResumeDecision(): Promise<ResumeDecisionEnvelope> {
  return fetchJson<ResumeDecisionEnvelope>('/api/v1/sessions/current/resume-decision');
}

export async function fetchRoleCatalog(): Promise<RoleCatalogEnvelope> {
  return fetchJson<RoleCatalogEnvelope>('/api/v1/roles');
}

export async function fetchCommandPolicies(): Promise<CommandPolicyCatalogEnvelope> {
  return fetchJson<CommandPolicyCatalogEnvelope>('/api/v1/command-policies');
}

export async function fetchCurrentEventLogIndex(): Promise<EventLogIndexEnvelope> {
  return fetchJson<EventLogIndexEnvelope>('/api/v1/sessions/current/event-log-index');
}

export async function fetchCurrentRecoveryTimeline(): Promise<RecoveryTimelineEnvelope> {
  return fetchJson<RecoveryTimelineEnvelope>('/api/v1/sessions/current/recovery-timeline');
}


export async function fetchCurrentResumeAttempts(): Promise<ResumeAttemptsEnvelope> {
  return fetchJson<ResumeAttemptsEnvelope>('/api/v1/sessions/current/resume-attempts');
}

export async function fetchCurrentResumeOutcomes(): Promise<ResumeAttemptOutcomesEnvelope> {
  return fetchJson<ResumeAttemptOutcomesEnvelope>('/api/v1/sessions/current/resume-outcomes');
}

export async function fetchCurrentCommandPolicy(): Promise<CommandPolicyCatalogEnvelope> {
  return fetchJson<CommandPolicyCatalogEnvelope>('/api/v1/sessions/current/command-policy');
}

export async function fetchCurrentCommandPolicySnapshot(): Promise<CommandPolicySnapshotEnvelope> {
  return fetchJson<CommandPolicySnapshotEnvelope>('/api/v1/sessions/current/command-policy-snapshot');
}

export async function fetchCurrentContractKernelDiff(): Promise<ContractKernelDiffEnvelope> {
  return fetchJson<ContractKernelDiffEnvelope>('/api/v1/sessions/current/contract-kernel-diff');
}

export async function fetchCurrentContractConsistency(): Promise<ContractConsistencyEnvelope> {
  return fetchJson<ContractConsistencyEnvelope>('/api/v1/sessions/current/contract-consistency');
}

export async function fetchCurrentReleaseEvidence(): Promise<ReleaseEvidenceEnvelope> {
  return fetchJson<ReleaseEvidenceEnvelope>('/api/v1/sessions/current/release-evidence');
}

export async function fetchCurrentEventDeliverySummary(): Promise<EventDeliverySummaryEnvelope> {
  return fetchJson<EventDeliverySummaryEnvelope>('/api/v1/sessions/current/event-delivery-summary');
}

export async function fetchEventDeliveryAudit(): Promise<EventDeliveryAuditEnvelope> {
  return fetchJson<EventDeliveryAuditEnvelope>('/api/v1/events/delivery-audit');
}

export async function fetchEventReplay(params: {
  topics?: string[];
  sessionId?: string;
  sinceTsNs?: number;
  untilTsNs?: number;
  delivery?: string;
  category?: string;
  limit?: number;
} = {}): Promise<EventReplayEnvelope> {
  const query = new URLSearchParams();
  if (params.topics?.length) query.set('topics', params.topics.join(','));
  if (params.sessionId) query.set('session_id', params.sessionId);
  if (params.sinceTsNs !== undefined) query.set('since_ts_ns', String(params.sinceTsNs));
  if (params.untilTsNs !== undefined) query.set('until_ts_ns', String(params.untilTsNs));
  if (params.delivery) query.set('delivery', params.delivery);
  if (params.category) query.set('category', params.category);
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  const suffix = query.toString();
  return fetchJson<EventReplayEnvelope>(`/api/v1/events/replay${suffix ? `?${suffix}` : ''}`);
}


export async function fetchEventBusStats(): Promise<EventBusStatsEnvelope> {
  return fetchJson<EventBusStatsEnvelope>('/api/v1/events/bus-stats');
}

export async function fetchEventDeadLetters(): Promise<DeadLetterEnvelope> {
  return fetchJson<DeadLetterEnvelope>('/api/v1/events/dead-letters');
}


export async function fetchCurrentSelectedExecutionRationale(): Promise<SelectedExecutionRationaleEnvelope> {
  const response = await fetch(apiUrl('/api/v1/sessions/current/selected-execution-rationale'));
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchCurrentReleaseGateDecision(): Promise<ReleaseGateDecisionEnvelope> {
  const response = await fetch(apiUrl('/api/v1/sessions/current/release-gate'));
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
