import { useRef, useEffect } from 'react';
import { useSessionStore } from '../store/sessionStore';

const levelColors = {
  info: 'text-clinical-cyan',
  success: 'text-clinical-emerald',
  warn: 'text-clinical-amber',
  error: 'text-clinical-error',
};

export default function SystemLog() {
  const logs = useSessionStore(s => s.logs);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new log
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs.length]);

  return (
    <div className="glass-panel p-3 w-80 max-h-48 shadow-[0_0_20px_rgba(0,0,0,0.5)] animate-fade-in-up flex flex-col">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-2 shrink-0">系统日志</h3>
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-0.5 min-h-0">
        {logs.map((entry, i) => (
          <div key={i} className="flex text-[10px] font-mono leading-relaxed">
            <span className="text-gray-600 shrink-0 mr-2">{entry.time}</span>
            <span className={`${levelColors[entry.level]}`}>{entry.msg}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
