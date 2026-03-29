import { useUIStore } from '../store/uiStore';
import { useSessionStore } from '../store/sessionStore';
import {
  ActivitySquare,
  ChevronLeft,
  ChevronRight,
  Cuboid,
  Download,
  FileStack,
  Joystick,
  Microscope,
  MonitorPlay,
  Radiation,
  ScrollText,
  Settings,
  UserCog,
} from 'lucide-react';

type PanelKey = 'showCamera' | 'showUltrasound' | 'showForceGraph' | 'show3DView' | 'showJoints' | 'showLog' | 'showReport' | 'showAlarms' | 'showConsole';

function Toggle({ id, label, Icon, active }: { id: PanelKey; label: string; Icon: any; active: boolean }) {
  const toggle = useUIStore((s) => s.togglePanel);
  return (
    <button
      onClick={() => toggle(id)}
      className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg border w-full text-left transition-all duration-200
        ${active ? 'bg-clinical-cyan/15 border-clinical-cyan/40 shadow-[0_0_12px_rgba(0,229,255,0.15)]' : 'bg-white/[0.02] border-white/5 opacity-50 hover:opacity-80'}`}
    >
      <Icon className={`w-4 h-4 shrink-0 ${active ? 'text-clinical-cyan' : 'text-gray-500'}`} />
      <span className={`font-mono text-xs tracking-wider ${active ? 'text-white' : 'text-gray-500'}`}>{label}</span>
    </button>
  );
}

export default function Sidebar() {
  const {
    sidebarOpen,
    toggleSidebar,
    setWorkspace,
    workspace,
    showCamera,
    showUltrasound,
    showForceGraph,
    show3DView,
    showJoints,
    showLog,
    showReport,
    showAlarms,
    showConsole,
  } = useUIStore();
  const exportCSV = useSessionStore((s) => s.exportCSV);

  return (
    <div className={`pointer-events-auto flex transition-all duration-300 ${sidebarOpen ? 'w-72' : 'w-10'}`}>
      <div className={`glass-panel overflow-hidden transition-all duration-300 flex flex-col shadow-[0_0_40px_rgba(0,0,0,0.6)] ${sidebarOpen ? 'w-68 p-4' : 'w-0 p-0 border-0'}`}>
        {sidebarOpen && (
          <div className="animate-fade-in-up flex flex-col space-y-4 min-w-[240px]">
            <div>
              <h2 className="text-gray-500 text-[10px] font-bold tracking-[0.2em] uppercase mb-2 flex items-center">
                <UserCog className="w-3 h-3 mr-1.5" /> 工作面
              </h2>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setWorkspace('operator')}
                  className={`px-3 py-2 rounded-lg border text-xs font-mono ${workspace === 'operator' ? 'bg-clinical-cyan/15 border-clinical-cyan/40 text-white' : 'bg-white/[0.02] border-white/5 text-gray-500'}`}
                >
                  操作者
                </button>
                <button
                  onClick={() => setWorkspace('researcher')}
                  className={`px-3 py-2 rounded-lg border text-xs font-mono ${workspace === 'researcher' ? 'bg-clinical-emerald/15 border-clinical-emerald/40 text-white' : 'bg-white/[0.02] border-white/5 text-gray-500'}`}
                >
                  研究者
                </button>
              </div>
            </div>

            <div>
              <h2 className="text-gray-500 text-[10px] font-bold tracking-[0.2em] uppercase mb-2 flex items-center">
                <Settings className="w-3 h-3 mr-1.5" /> 显示控制
              </h2>
              <div className="flex flex-col space-y-1.5">
                <Toggle id="showCamera" label="RGB 摄像头" Icon={MonitorPlay} active={showCamera} />
                <Toggle id="showUltrasound" label="超声 B 模式" Icon={Radiation} active={showUltrasound} />
                <Toggle id="showForceGraph" label="力传感器" Icon={ActivitySquare} active={showForceGraph} />
                <Toggle id="show3DView" label="3D 轨迹" Icon={Cuboid} active={show3DView} />
                <Toggle id="showJoints" label="关节角度" Icon={Joystick} active={showJoints} />
                <Toggle id="showLog" label="系统日志" Icon={ScrollText} active={showLog} />
                <Toggle id="showReport" label="会话报告" Icon={Microscope} active={showReport} />
                <Toggle id="showAlarms" label="告警时间线" Icon={ActivitySquare} active={showAlarms} />
                <Toggle id="showConsole" label="会话控制台" Icon={FileStack} active={showConsole} />
              </div>
            </div>

            <div className="border-t border-white/5" />

            <div>
              <h2 className="text-gray-500 text-[10px] font-bold tracking-[0.2em] uppercase mb-2">数据导出</h2>
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

      <button
        onClick={toggleSidebar}
        className="h-10 w-6 self-center -ml-px bg-clinical-surface/80 border border-white/10 rounded-r-lg flex items-center justify-center hover:bg-clinical-cyan/20 transition-all"
      >
        {sidebarOpen ? <ChevronLeft className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </button>
    </div>
  );
}
