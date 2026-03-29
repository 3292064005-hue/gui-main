import type { ReactNode } from 'react';

export default function OperatorWorkspace({ children }: { children?: ReactNode }) {
  return <div data-workspace="operator" className="workspace-shell workspace-operator">{children}</div>;
}
