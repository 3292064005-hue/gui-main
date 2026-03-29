import type { DeviceReadinessEnvelope } from '../api/client';

const ITEMS: Array<[keyof DeviceReadinessEnvelope, string]> = [
  ['robot_ready', '机械臂'],
  ['camera_ready', '相机'],
  ['ultrasound_ready', '超声'],
  ['force_provider_ready', '压力传感器'],
  ['storage_ready', '存储'],
  ['config_valid', '配置'],
  ['protocol_match', '协议'],
  ['time_sync_ok', '时间同步'],
  ['network_link_ok', '网络链路'],
  ['single_control_source_ok', '单控制源'],
  ['rt_control_ready', 'RT 控制'],
];

export default function SystemReadinessPanel({ readiness }: { readiness: DeviceReadinessEnvelope | null }) {
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">System Readiness</h3>
      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-gray-200">
        {ITEMS.map(([key, label]) => {
          const ok = readiness?.[key] === true;
          return (
            <div key={String(key)} className={`rounded-lg border px-3 py-2 ${ok ? 'border-clinical-emerald/30 bg-clinical-emerald/10' : 'border-white/10 bg-white/[0.03]'}`}>
              <div className="text-gray-400">{label}</div>
              <div className={ok ? 'text-clinical-emerald' : 'text-clinical-amber'}>{ok ? 'ready' : 'check'}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
