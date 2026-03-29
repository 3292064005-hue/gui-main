import type { ReactNode } from 'react';

export default function ResearchWorkspace({ children }: { children?: ReactNode }) {
  return <div data-workspace="research" className="workspace-shell workspace-research">{children}</div>;
}
