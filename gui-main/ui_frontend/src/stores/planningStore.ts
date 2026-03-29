import { create } from 'zustand';

interface PlanningDomainState {
  selectedPlanId: string;
  candidateCount: number;
  selectedRationale: Record<string, unknown> | null;
  patchWindowCount: number;
  resumeMode: string;
  setPlanningDomain: (payload: Partial<PlanningDomainState>) => void;
}

export const usePlanningDomainStore = create<PlanningDomainState>((set) => ({
  selectedPlanId: '',
  candidateCount: 0,
  selectedRationale: null,
  patchWindowCount: 0,
  resumeMode: 'manual_review',
  setPlanningDomain: (payload) => set((state) => ({ ...state, ...payload })),
}));
