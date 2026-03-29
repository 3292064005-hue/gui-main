import type { AssessmentEnvelope } from '../api/client';

export default function AssessmentReviewDesk({ assessment }: { assessment: AssessmentEnvelope | null }) {
  const evidence = assessment?.evidence_frames ?? [];
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Assessment Review</h3>
      <div className="space-y-3 text-[11px] font-mono text-white">
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">Confidence</div><div>{String(assessment?.confidence ?? '-')}</div></div>
          <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">Manual review</div><div>{assessment?.requires_manual_review ? 'required' : 'not required'}</div></div>
          <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">Cobb candidate</div><div>{assessment?.cobb_candidate_deg ?? '-'}</div></div>
          <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="text-gray-400">Landmarks</div><div>{assessment?.landmark_candidates?.length ?? 0}</div></div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
          <div className="text-gray-400">Curve candidate</div>
          <div className="mt-1 text-gray-200">{String(assessment?.curve_candidate?.description ?? assessment?.curve_candidate?.status ?? '暂无')}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
          <div className="text-gray-400 mb-2">Evidence frames</div>
          <div className="space-y-1 max-h-32 overflow-y-auto custom-scrollbar">
            {evidence.length === 0 ? <div className="text-gray-500">暂无证据帧</div> : evidence.map((frame, index) => (
              <div key={`${frame.frame_id ?? index}-${frame.ts_ns ?? index}`} className="flex items-center justify-between gap-2 text-gray-200">
                <span>frame {String(frame.frame_id ?? index)}</span>
                <span>seg {String(frame.segment_id ?? '-')}</span>
                <span>q {String(frame.quality_score ?? '-')}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
