import { motion } from 'framer-motion';

interface Props {
  latestForce: number;
  maxForce: number;
  targetForce: number;
}

export default function ForceGraph({ latestForce, maxForce, targetForce }: Props) {
  const ratio = Math.min(Math.abs(latestForce) / maxForce, 1.0);
  const deviation = Math.abs(latestForce - targetForce);

  // Multi-zone color: green = on target, amber = drifting, red = danger
  let barColor = 'bg-clinical-emerald';
  let textColor = 'text-clinical-emerald';
  let label = '精准';
  if (deviation >= 3.0) {
    barColor = 'bg-clinical-error';
    textColor = 'text-clinical-error';
    label = '危险';
  } else if (deviation >= 1.0) {
    barColor = 'bg-clinical-amber';
    textColor = 'text-clinical-amber';
    label = '偏移';
  }

  return (
    <div className="flex flex-col space-y-2.5">
      <div className="flex justify-between items-baseline font-mono">
        <span className="text-gray-500 text-[10px] uppercase tracking-widest">测量值</span>
        <div className="flex items-baseline space-x-2">
          <span className={`text-[10px] font-medium tracking-widest ${textColor}`}>{label}</span>
          <span className={`text-2xl font-bold ${textColor}`}>
            {latestForce.toFixed(2)} <span className="text-base font-normal">N</span>
          </span>
        </div>
      </div>

      {/* Progress bar with warning zones */}
      <div className="relative h-3.5 w-full bg-clinical-bg rounded-lg overflow-hidden border border-white/10">
        {/* Danger zones (subtle background hints) */}
        <div className="absolute inset-0 flex">
          <div className="w-[46.7%] bg-clinical-error/5" />  {/* 0-7N: low danger */}
          <div className="w-[13.3%] bg-clinical-amber/5" />  {/* 7-9N: amber */}
          <div className="w-[13.3%] bg-clinical-emerald/5" />{/* 9-11N: green target */}
          <div className="w-[13.3%] bg-clinical-amber/5" />  {/* 11-13N: amber */}
          <div className="w-[13.3%] bg-clinical-error/5" />  {/* 13-15N: high danger */}
        </div>

        {/* Active bar */}
        <motion.div
          className={`absolute top-0 left-0 h-full ${barColor} shadow-[0_0_8px_rgba(0,229,255,0.3)]`}
          initial={{ width: 0 }}
          animate={{ width: `${ratio * 100}%` }}
          transition={{ type: "spring", bounce: 0.05, duration: 0.08 }}
        />

        {/* 10N Target Notch */}
        <div className="absolute top-0 bottom-0 w-0.5 bg-white/60 z-10" style={{ left: `${(targetForce / maxForce) * 100}%` }} />
      </div>

      <div className="flex justify-between text-[9px] text-gray-600 font-mono tracking-widest">
        <span>0N</span>
        <span>目标 ({targetForce.toFixed(1)}N)</span>
        <span>{maxForce}N (极限)</span>
      </div>
    </div>
  );
}
