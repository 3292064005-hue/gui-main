import type { ScanProtocolEnvelope } from '../api/client';

export default function ScanProtocolPanel({ protocol }: { protocol: ScanProtocolEnvelope | null }) {
  const pathPolicy = protocol?.path_policy as Record<string, unknown> | undefined;
  const contact = protocol?.contact_control as Record<string, unknown> | undefined;
  return (
    <div className="glass-panel p-4 shadow-[0_0_20px_rgba(0,0,0,0.4)]">
      <h3 className="text-[10px] text-gray-400 font-bold tracking-widest uppercase mb-3">Scan Protocol</h3>
      <div className="space-y-2 text-[11px] font-mono text-gray-200">
        <div>Protocol: {String(protocol?.protocol_id ?? '-')}</div>
        <div>扫描策略: {String(pathPolicy?.pattern ?? pathPolicy?.policy ?? '-')}</div>
        <div>条带宽度: {typeof pathPolicy?.strip_width_mm === 'number' ? `${pathPolicy.strip_width_mm} mm` : '-'}</div>
        <div>重叠: {typeof pathPolicy?.strip_overlap_mm === 'number' ? `${pathPolicy.strip_overlap_mm} mm` : '-'}</div>
        <div>目标接触力: {typeof contact?.target_force_n === 'number' ? `${contact.target_force_n.toFixed(1)} N` : '-'}</div>
      </div>
    </div>
  );
}
