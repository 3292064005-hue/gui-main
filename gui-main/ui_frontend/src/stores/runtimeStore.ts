import { create } from 'zustand';

interface RuntimeDomainState {
  executionState: string;
  recoveryState: string;
  contactState: string;
  commandAvailability: Record<string, boolean>;
  commandPolicyVersion: string;
  setRuntimeSnapshot: (payload: Partial<RuntimeDomainState>) => void;
}

export const useRuntimeDomainStore = create<RuntimeDomainState>((set) => ({
  executionState: 'BOOT',
  recoveryState: 'IDLE',
  contactState: 'NO_CONTACT',
  commandAvailability: {},
  commandPolicyVersion: '',
  setRuntimeSnapshot: (payload) => set((state) => ({ ...state, ...payload })),
}));
