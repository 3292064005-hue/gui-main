import { useUIStore } from '../store/uiStore';
import { ShieldCheck, ShieldAlert, Info, AlertTriangle } from 'lucide-react';

const iconMap = {
  info: <Info className="w-5 h-5 text-clinical-cyan shrink-0" />,
  success: <ShieldCheck className="w-5 h-5 text-clinical-emerald shrink-0" />,
  error: <ShieldAlert className="w-5 h-5 text-clinical-error shrink-0" />,
  warn: <AlertTriangle className="w-5 h-5 text-clinical-amber shrink-0" />,
};

const bgMap = {
  info: 'border-clinical-cyan/30 bg-clinical-cyan/10',
  success: 'border-clinical-emerald/30 bg-clinical-emerald/10',
  error: 'border-clinical-error/30 bg-clinical-error/10',
  warn: 'border-clinical-amber/30 bg-clinical-amber/10',
};

export default function ToastContainer() {
  const toasts = useUIStore(s => s.toasts);

  return (
    <div className="fixed top-20 right-6 z-[100] flex flex-col space-y-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`animate-slide-in-right pointer-events-auto flex items-center space-x-3 px-4 py-3 rounded-xl border backdrop-blur-xl shadow-2xl max-w-sm ${bgMap[t.type]}`}
        >
          {iconMap[t.type]}
          <span className="text-sm font-mono text-white/90">{t.msg}</span>
        </div>
      ))}
    </div>
  );
}
