import { create } from 'zustand';

export type Workspace = 'operator' | 'researcher';

type ToastType = 'info' | 'success' | 'error' | 'warn';
type PanelKey = 'showCamera' | 'showUltrasound' | 'showForceGraph' | 'show3DView' | 'showJoints' | 'showLog' | 'showReport' | 'showAlarms' | 'showConsole';

interface UIPersistedState {
  workspace: Workspace;
  showCamera: boolean;
  showUltrasound: boolean;
  showForceGraph: boolean;
  show3DView: boolean;
  showJoints: boolean;
  showLog: boolean;
  showReport: boolean;
  showAlarms: boolean;
  showConsole: boolean;
  sidebarOpen: boolean;
}

interface UIState extends UIPersistedState {
  toasts: { id: number; msg: string; type: ToastType }[];
  setWorkspace: (workspace: Workspace) => void;
  togglePanel: (panel: PanelKey) => void;
  setSidebar: (v: boolean) => void;
  toggleSidebar: () => void;
  addToast: (msg: string, type?: ToastType) => void;
  removeToast: (id: number) => void;
}

const STORAGE_KEY = 'spine.desktop.ui';

function loadPersistedState(): UIPersistedState {
  const defaults: UIPersistedState = {
    workspace: 'operator',
    showCamera: true,
    showUltrasound: true,
    showForceGraph: true,
    show3DView: true,
    showJoints: false,
    showLog: true,
    showReport: true,
    showAlarms: true,
    showConsole: true,
    sidebarOpen: true,
  };
  if (typeof window === 'undefined') return defaults;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Partial<UIPersistedState>;
    return { ...defaults, ...parsed };
  } catch {
    return defaults;
  }
}

function persistState(state: UIPersistedState): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore persistence failures in constrained environments
  }
}

let toastId = 0;
const initial = loadPersistedState();

export const useUIStore = create<UIState>((set, get) => ({
  ...initial,
  toasts: [],

  setWorkspace: (workspace) => {
    set({ workspace });
    persistState({ ...getPersisted(get()), workspace });
  },

  togglePanel: (panel) => {
    const nextValue = !get()[panel];
    set({ [panel]: nextValue } as Pick<UIState, typeof panel>);
    persistState({ ...getPersisted(get()), [panel]: nextValue });
  },

  setSidebar: (v) => {
    set({ sidebarOpen: v });
    persistState({ ...getPersisted(get()), sidebarOpen: v });
  },

  toggleSidebar: () => {
    const next = !get().sidebarOpen;
    set({ sidebarOpen: next });
    persistState({ ...getPersisted(get()), sidebarOpen: next });
  },

  addToast: (msg, type = 'info') => {
    const id = ++toastId;
    set((s) => ({ toasts: [...s.toasts, { id, msg, type }] }));
    setTimeout(() => get().removeToast(id), 3000);
  },

  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

function getPersisted(state: UIState): UIPersistedState {
  return {
    workspace: state.workspace,
    showCamera: state.showCamera,
    showUltrasound: state.showUltrasound,
    showForceGraph: state.showForceGraph,
    show3DView: state.show3DView,
    showJoints: state.showJoints,
    showLog: state.showLog,
    showReport: state.showReport,
    showAlarms: state.showAlarms,
    showConsole: state.showConsole,
    sidebarOpen: state.sidebarOpen,
  };
}
