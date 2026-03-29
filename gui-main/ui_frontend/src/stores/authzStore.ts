import { create } from 'zustand';

interface AuthzDomainState {
  role: string;
  canExport: boolean;
  canControl: boolean;
  topicPermissions: string[];
  commandPolicies: Record<string, Record<string, unknown>>;
  setAuthzDomain: (payload: Partial<AuthzDomainState>) => void;
}

export const useAuthzDomainStore = create<AuthzDomainState>((set) => ({
  role: 'operator',
  canExport: true,
  canControl: true,
  topicPermissions: [],
  commandPolicies: {},
  setAuthzDomain: (payload) => set((state) => ({ ...state, ...payload })),
}));
