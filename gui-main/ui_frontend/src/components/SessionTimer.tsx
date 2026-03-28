import { useEffect, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { Timer } from 'lucide-react';

export default function SessionTimer() {
  const { scanState, startTime, frameCount, sessionId } = useSessionStore();
  const [elapsed, setElapsed] = useState('00:00');

  useEffect(() => {
    if (scanState !== 'scanning' || !startTime) {
      setElapsed('00:00');
      return;
    };
    const iv = setInterval(() => {
      const diff = Math.floor((Date.now() - startTime) / 1000);
      const m = String(Math.floor(diff / 60)).padStart(2, '0');
      const s = String(diff % 60).padStart(2, '0');
      setElapsed(`${m}:${s}`);
    }, 200);
    return () => clearInterval(iv);
  }, [scanState, startTime]);

  if (scanState !== 'scanning') return null;

  return (
    <div className="glass-panel px-4 py-2 flex items-center space-x-3 pointer-events-auto animate-fade-in-up shadow-[0_0_20px_rgba(0,0,0,0.5)]">
      <Timer className="w-4 h-4 text-clinical-emerald animate-pulse" />
      <div className="font-mono">
        <div className="text-clinical-emerald text-lg font-bold tracking-wider">{elapsed}</div>
        <div className="text-[9px] text-gray-500 tracking-widest">{frameCount} 帧 · {sessionId}</div>
      </div>
    </div>
  );
}
