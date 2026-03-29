import { create } from 'zustand';

interface DiagnosticsDomainState {
  continuityGapCount: number;
  incidentCount: number;
  resumeViability: Record<string, unknown> | null;
  releaseEvidence: Record<string, unknown> | null;
  setDiagnosticsDomain: (payload: Partial<DiagnosticsDomainState>) => void;
}

export const useDiagnosticsDomainStore = create<DiagnosticsDomainState>((set) => ({
  continuityGapCount: 0,
  incidentCount: 0,
  resumeViability: null,
  releaseEvidence: null,
  setDiagnosticsDomain: (payload) => set((state) => ({ ...state, ...payload })),
}));
