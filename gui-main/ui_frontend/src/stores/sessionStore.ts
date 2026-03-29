import { create } from 'zustand';

interface SessionDomainState {
  sessionId: string | null;
  artifactSummary: Record<string, unknown> | null;
  eventContinuity: Record<string, unknown> | null;
  replayStatus: Record<string, unknown> | null;
  releaseEvidence: Record<string, unknown> | null;
  setSessionDomain: (payload: Partial<SessionDomainState>) => void;
}

export const useSessionDomainStore = create<SessionDomainState>((set) => ({
  sessionId: null,
  artifactSummary: null,
  eventContinuity: null,
  replayStatus: null,
  releaseEvidence: null,
  setSessionDomain: (payload) => set((state) => ({ ...state, ...payload })),
}));
