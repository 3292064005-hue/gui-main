import type { ArtifactsEnvelope } from '../api/client';

export default function ArtifactExplorerPanel({ artifacts }: { artifacts: ArtifactsEnvelope | null }) {
  const entries = Object.values(artifacts?.artifact_registry ?? {}).slice(0, 8);
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Artifact Explorer</h3>
      <div className="space-y-2 text-[11px] font-mono text-gray-200 max-h-56 overflow-y-auto custom-scrollbar">
        {entries.length === 0 ? <div className="text-gray-500">暂无产物</div> : entries.map((artifact) => (
          <div key={artifact.artifact_id} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <div>{artifact.artifact_type}</div>
            <div className="text-gray-400">{artifact.ready ? 'ready' : 'pending'} · {artifact.source_stage || '-'}</div>
            <div className="text-gray-500 truncate">deps: {(artifact.dependencies ?? []).join(', ') || '-'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
