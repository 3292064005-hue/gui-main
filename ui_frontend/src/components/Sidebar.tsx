import { useUIStore } from '../store/uiStore';
import { useSessionStore } from '../store/sessionStore';
import {
  MonitorPlay, Radiation, ActivitySquare, Cuboid, ScrollText,
  Joystick, Download, ChevronLeft, ChevronRight, Settings
} from 'lucide-react';

function Toggle({ id, label, Icon, active }: { id: string; label: string; Icon: any; active: boolean }) {
  const toggle = useUIStore(s => s.togglePanel);
  return (
    <button
      onClick={() => toggle(id)}
      className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg border w-full text-left transition-all duration-200
        ${active
          ? 'bg-clinical-cyan/15 border-clinical-cyan/40 shadow-[0_0_12px_rgba(0,229,255,0.15)]'
          : 'bg-white/[0.02] border-white/5 opacity-50 hover:opacity-80'}`}
    >
      <Icon className={`w-4 h-4 shrink-0 ${active ? 'text-clinical-cyan' : 'text-gray-500'}`} />
      <span className={`font-mono text-xs tracking-wider ${active ? 'text-white' : 'text-gray-500'}`}>{label}</span>
    </button>
  );
}

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar, showCamera, showUltrasound, showForceGraph, show3DView, showJoints, showLog, showReport, showAlarms } = useUIStore();
  const exportCSV = useSessionStore(s => s.exportCSV);

  return (
    <div className={`pointer-events-auto flex transition-all duration-300 ${sidebarOpen ? 'w-60' : 'w-10'}`}>
      {/* Sidebar Content */}
      <div className={`glass-panel overflow-hidden transition-all duration-300 flex flex-col shadow-[0_0_40px_rgba(0,0,0,0.6)] ${sidebarOpen ? 'w-56 p-4' : 'w-0 p-0 border-0'}`}>
        {sidebarOpen && (
          <div className="animate-fade-in-up flex flex-col space-y-4 min-w-[200px]">
            {/* Section: Displays */}
            <div>
              <h2 className="text-gray-500 text-[10px] font-bold tracking-[0.2em] uppercase mb-2 flex items-center">
                <Settings className="w-3 h-3 mr-1.5" />
                显示控制
              </h2>
              <div className="flex flex-col space-y-1.5">
                <Toggle id="showCamera"     label="RGB 摄像头"    Icon={MonitorPlay}   active={showCamera} />
                <Toggle id="showUltrasound"  label="超声 B 模式"   Icon={Radiation}     active={showUltrasound} />
                <Toggle id="showForceGraph"  label="力传感器"      Icon={ActivitySquare} active={showForceGraph} />
                <Toggle id="show3DView"      label="3D 雷达"      Icon={Cuboid}         active={show3DView} />
                <Toggle id="showJoints"      label="关节角度"      Icon={Joystick}       active={showJoints} />
                <Toggle id="showLog"         label="系统日志"      Icon={ScrollText}     active={showLog} />
                <Toggle id="showReport"      label="会话报告"      Icon={Download}       active={showReport} />
                <Toggle id="showAlarms"      label="告警时间线"    Icon={ActivitySquare} active={showAlarms} />
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-white/5" />

            {/* Section: Data */}
            <div>
              <h2 className="text-gray-500 text-[10px] font-bold tracking-[0.2em] uppercase mb-2">
                数据导出
              </h2>
              <button
                onClick={exportCSV}
                className="flex items-center space-x-2 px-3 py-2 rounded-lg border border-clinical-emerald/30 bg-clinical-emerald/10 w-full hover:bg-clinical-emerald/20 transition-all"
              >
                <Download className="w-4 h-4 text-clinical-emerald" />
                <span className="font-mono text-xs text-clinical-emerald tracking-wider">导出力数据 CSV</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Toggle Tab */}
      <button
        onClick={toggleSidebar}
        className="h-10 w-6 self-center -ml-px bg-clinical-surface/80 border border-white/10 rounded-r-lg flex items-center justify-center hover:bg-clinical-cyan/20 transition-all"
      >
        {sidebarOpen ? <ChevronLeft className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </button>
    </div>
  );
}
