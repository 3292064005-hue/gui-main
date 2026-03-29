import { useTelemetryStore } from '../store/telemetryStore';

const JOINT_LABELS = ['J1 底座', 'J2 肩部', 'J3 肘部', 'J4 腕旋', 'J5 腕弯', 'J6 腕转'];
const MAX_DEG = 180;

export default function JointAnglePanel() {
  const joints = useTelemetryStore((s) => s.joints);

  return (
    <div className="glass-panel p-3 w-52 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up">
      <h3 className="text-[10px] text-clinical-cyan font-bold tracking-widest uppercase mb-2">关节角度 (6-DOF)</h3>
      <div className="space-y-1.5">
        {joints.map((val, i) => {
          const deg = val * (180 / Math.PI);
          const ratio = Math.min(Math.abs(deg) / MAX_DEG, 1);
          const color = ratio > 0.85 ? 'bg-clinical-error' : ratio > 0.65 ? 'bg-clinical-amber' : 'bg-clinical-cyan';
          return (
            <div key={i}>
              <div className="flex justify-between items-baseline">
                <span className="text-[9px] text-gray-500 font-mono">{JOINT_LABELS[i] ?? `J${i + 1}`}</span>
                <span className="text-[10px] text-white font-mono">{deg.toFixed(1)}°</span>
              </div>
              <div className="h-1.5 w-full bg-clinical-bg rounded-full overflow-hidden border border-white/5">
                <div className={`h-full rounded-full transition-all duration-100 ${color}`} style={{ width: `${ratio * 100}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
