import type { ReactNode } from 'react';

export default function ReviewWorkspace({ children }: { children?: ReactNode }) {
  return <div data-workspace="review" className="workspace-shell workspace-review">{children}</div>;
}
