import type { ReactNode } from 'react';

export default function QaWorkspace({ children }: { children?: ReactNode }) {
  return <div data-workspace="qa" className="workspace-shell workspace-qa">{children}</div>;
}
