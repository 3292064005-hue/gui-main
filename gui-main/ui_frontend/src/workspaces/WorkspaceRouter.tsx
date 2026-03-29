import type { ReactNode } from 'react';
import type { Workspace } from '../store/uiStore';
import OperatorWorkspace from './operator';
import ResearchWorkspace from './research';
import QaWorkspace from './qa';
import ReviewWorkspace from './review';

export default function WorkspaceRouter({ workspace, children }: { workspace: Workspace; children?: ReactNode }) {
  if (workspace === 'qa') return <QaWorkspace>{children}</QaWorkspace>;
  if (workspace === 'review') return <ReviewWorkspace>{children}</ReviewWorkspace>;
  if (workspace === 'researcher') return <ResearchWorkspace>{children}</ResearchWorkspace>;
  return <OperatorWorkspace>{children}</OperatorWorkspace>;
}
