import { useTelemetryStore } from '../store/telemetryStore';
import { useSessionStore } from '../store/sessionStore';
import { useUIStore } from '../store/uiStore';
import { Gauge, MonitorDot, Wifi, WifiOff } from 'lucide-react';

export default function StatusBar() {
  const { connected, latencyMs, fps, telemetryStale } = useTelemetryStore();
  const { scanState, sessionId } = useSessionStore();
  const workspace = useUIStore((s) => s.workspace);

  const stateLabel: Record<string, [string, string]> = {
    idle: ['待机', 'text-gray-400'],
    scanning: ['扫描中', 'text-clinical-emerald'],
    paused: ['保持中', 'text-clinical-cyan'],
    halted: ['已制动', 'text-clinical-error'],
  };
  const [label, color] = stateLabel[scanState] || ['未知', 'text-gray-400'];

  return (
    <div className="absolute bottom-0 left-0 right-0 h-7 bg-clinical-surface/70 backdrop-blur-lg border-t border-white/5 flex items-center justify-between px-4 text-[10px] font-mono text-gray-500 z-20 pointer-events-none">
      <div className="flex items-center space-x-4">
        <span className="flex items-center space-x-1">
          {connected ? <Wifi className="w-3 h-3 text-clinical-emerald" /> : <WifiOff className="w-3 h-3 text-clinical-error" />}
          <span>{connected ? '已连接' : '未连接'}</span>
        </span>
        <span className="flex items-center space-x-1"><Gauge className="w-3 h-3" /><span>{latencyMs}ms</span></span>
        <span className={telemetryStale ? 'text-clinical-error' : 'text-clinical-emerald'}>{telemetryStale ? 'STALE' : 'FRESH'}</span>
        <span className="flex items-center space-x-1"><MonitorDot className="w-3 h-3" /><span>{fps} FPS</span></span>
      </div>
      <span className={color}>{label}</span>
      <span className="text-gray-600">{workspace === 'operator' ? '操作者工作面' : '研究者工作面'} · {sessionId || '无会话'} · ROKAE xMate ER3</span>
    </div>
  );
}
