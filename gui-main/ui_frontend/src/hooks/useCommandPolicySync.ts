import { useEffect, useMemo, useState } from "react";

import { fetchCommandPolicies, type CommandPolicyCatalogEnvelope } from "../api/client";
import { useAuthzDomainStore } from "../stores/authzStore";
import { useRuntimeDomainStore } from "../stores/runtimeStore";

interface UseCommandPolicySyncOptions {
  workspace: string;
  executionState: string;
  contactState: string;
  planState?: string;
  resumeMode?: string;
  readOnlyMode: boolean;
}

export function useCommandPolicySync({ workspace, executionState, contactState, planState = '*', resumeMode = '*', readOnlyMode }: UseCommandPolicySyncOptions) {
  const [catalog, setCatalog] = useState<CommandPolicyCatalogEnvelope | null>(null);
  const setAuthzDomain = useAuthzDomainStore((s) => s.setAuthzDomain);
  const setRuntimeSnapshot = useRuntimeDomainStore((s) => s.setRuntimeSnapshot);

  useEffect(() => {
    let cancelled = false;
    fetchCommandPolicies().then((payload) => {
      if (cancelled) return;
      setCatalog(payload);
      const commandPolicies = Object.fromEntries((payload.policies ?? []).map((item) => [String(item.command), item]));
      setAuthzDomain({ commandPolicies });
    }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [setAuthzDomain]);

  const commandAvailability = useMemo(() => Object.fromEntries((catalog?.policies ?? []).map((item) => {
    const allowedStates = Array.isArray(item.allowed_states) ? item.allowed_states.map((state) => String(state)) : [];
    const roleGate = Array.isArray(item.role_write_gate) ? item.role_write_gate.map((role) => String(role)) : [];
    const requiredContact = Array.isArray(item.required_contact_state) ? item.required_contact_state.map((state) => String(state)) : ['*'];
    const requiredPlan = Array.isArray(item.required_plan_state) ? item.required_plan_state.map((state) => String(state)) : ['*'];
    const requiredResume = Array.isArray(item.required_resume_mode) ? item.required_resume_mode.map((state) => String(state)) : ['*'];
    const allowed = !readOnlyMode && roleGate.includes(workspace)
      && (allowedStates.includes('*') || allowedStates.includes(executionState))
      && (requiredContact.includes('*') || requiredContact.includes(contactState))
      && (requiredPlan.includes('*') || requiredPlan.includes(planState))
      && (requiredResume.includes('*') || requiredResume.includes(resumeMode));
    return [String(item.command), allowed];
  })), [catalog, workspace, executionState, contactState, planState, resumeMode, readOnlyMode]);

  useEffect(() => {
    setRuntimeSnapshot({ executionState, contactState, commandAvailability, commandPolicyVersion: catalog?.schema ?? '' });
  }, [catalog, commandAvailability, contactState, executionState, setRuntimeSnapshot]);

  const commandAllowed = useMemo(() => (command: string) => Boolean(commandAvailability?.[command]), [commandAvailability]);
  return { commandPolicyCatalog: catalog, commandAvailability, commandAllowed };
}
