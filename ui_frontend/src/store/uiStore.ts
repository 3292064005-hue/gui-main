import { create } from 'zustand';

interface UIState {
  // Panel visibility
  showCamera: boolean;
  showUltrasound: boolean;
  showForceGraph: boolean;
  show3DView: boolean;
  showJoints: boolean;
  showLog: boolean;
  showReport: boolean;
  showAlarms: boolean;

  // Sidebar
  sidebarOpen: boolean;

  // Toasts
  toasts: { id: number; msg: string; type: 'info' | 'success' | 'error' | 'warn' }[];

  // Actions
  togglePanel: (panel: string) => void;
  setSidebar: (v: boolean) => void;
  toggleSidebar: () => void;
  addToast: (msg: string, type?: 'info' | 'success' | 'error' | 'warn') => void;
  removeToast: (id: number) => void;
}

let toastId = 0;

export const useUIStore = create<UIState>((set, get) => ({
  showCamera: true,
  showUltrasound: true,
  showForceGraph: true,
  show3DView: true,
  showJoints: false,
  showLog: true,
  showReport: true,
  showAlarms: true,

  sidebarOpen: true,

  toasts: [],

  togglePanel: (panel) => set((s: any) => ({ [panel]: !s[panel] })),
  setSidebar: (v) => set({ sidebarOpen: v }),
  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),

  addToast: (msg, type = 'info') => {
    const id = ++toastId;
    set(s => ({ toasts: [...s.toasts, { id, msg, type }] }));
    // Auto-remove after 3s
    setTimeout(() => get().removeToast(id), 3000);
  },

  removeToast: (id) => set(s => ({
    toasts: s.toasts.filter(t => t.id !== id)
  })),
}));
