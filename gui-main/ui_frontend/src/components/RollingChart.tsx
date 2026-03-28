import { useRef, useCallback, useEffect, useState } from 'react';

interface Props {
  latestValue: number;
  color?: string;
  maxPoints?: number;
  maxVal?: number;
  targetValue?: number;
  width?: number;
  height?: number;
}

/**
 * High-performance rolling chart using circular buffer (no array copy per frame).
 * Renders via SVG polyline — bypasses React's DOM diff entirely.
 */
export default function RollingChart({
  latestValue,
  color = '#00E5FF',
  maxPoints = 150,
  maxVal = 15.0,
  targetValue = 10.0,
  width = 320,
  height = 110,
}: Props) {
  // Circular buffer
  const bufRef = useRef<Float64Array>(new Float64Array(maxPoints));
  const headRef = useRef(0);
  const [svgPath, setSvgPath] = useState('');
  const [fillPath, setFillPath] = useState('');
  const [stats, setStats] = useState({ min: 0, max: 0, avg: 0 });
  const [hoverInfo, setHoverInfo] = useState<{ x: number; y: number; val: number } | null>(null);

  // Push value into circular buffer (O(1))
  useEffect(() => {
    const buf = bufRef.current;
    buf[headRef.current % maxPoints] = latestValue;
    headRef.current++;

    // Build SVG points from circular buffer
    const points: string[] = [];
    let min = Infinity, max = -Infinity, sum = 0;
    const count = Math.min(headRef.current, maxPoints);

    for (let i = 0; i < count; i++) {
      const idx = (headRef.current - count + i) % maxPoints;
      const val = buf[idx < 0 ? idx + maxPoints : idx];
      const x = (i / maxPoints) * width;
      const y = height - Math.min((val / maxVal) * height, height);
      points.push(`${x.toFixed(1)},${y.toFixed(1)}`);

      if (val < min) min = val;
      if (val > max) max = val;
      sum += val;
    }

    const joined = points.join(' ');
    setSvgPath(joined);
    setFillPath(`0,${height} ${joined} ${width},${height}`);
    setStats({
      min: count > 0 ? min : 0,
      max: count > 0 ? max : 0,
      avg: count > 0 ? sum / count : 0,
    });
  }, [latestValue, maxPoints, maxVal, width, height]);

  const targetY = height - (targetValue / maxVal) * height;

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const idx = Math.round((x / width) * maxPoints);
    const buf = bufRef.current;
    const actualIdx = (headRef.current - maxPoints + idx) % maxPoints;
    const val = buf[actualIdx < 0 ? actualIdx + maxPoints : actualIdx] || 0;
    const y = height - Math.min((val / maxVal) * height, height);
    setHoverInfo({ x, y, val });
  }, [width, height, maxPoints, maxVal]);

  return (
    <div className="flex flex-col space-y-1">
      <div
        className="border border-white/10 bg-black/50 rounded-lg relative overflow-hidden"
        style={{ width, height }}
        onMouseLeave={() => setHoverInfo(null)}
      >
        <svg width={width} height={height} className="absolute inset-0" onMouseMove={handleMouseMove}>
          {/* Target line */}
          <line x1="0" y1={targetY} x2={width} y2={targetY} stroke="rgba(255,255,255,0.15)" strokeDasharray="4" strokeWidth="1" />

          {/* Fill */}
          <polyline points={fillPath} fill={color} fillOpacity="0.08" />
          {/* Line */}
          <polyline points={svgPath} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />

          {/* Hover crosshair */}
          {hoverInfo && (
            <>
              <line x1={hoverInfo.x} y1={0} x2={hoverInfo.x} y2={height} stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
              <circle cx={hoverInfo.x} cy={hoverInfo.y} r="3" fill={color} stroke="white" strokeWidth="1" />
            </>
          )}
        </svg>

        {/* Hover tooltip */}
        {hoverInfo && (
          <div
            className="absolute bg-black/80 text-white text-[10px] font-mono px-2 py-1 rounded pointer-events-none border border-white/10"
            style={{ left: Math.min(hoverInfo.x + 8, width - 60), top: Math.max(hoverInfo.y - 24, 4) }}
          >
            {hoverInfo.val.toFixed(3)} N
          </div>
        )}

        {/* Corner labels */}
        <span className="absolute top-0.5 left-1.5 text-[8px] text-gray-600 font-mono">{maxVal}N</span>
        <span className="absolute bottom-0.5 left-1.5 text-[8px] text-gray-600 font-mono">0N</span>
        <span className="absolute bottom-0.5 right-1.5 text-[8px] text-gray-600 font-mono">−{(maxPoints / 60).toFixed(1)}s</span>
      </div>

      {/* Stats row */}
      <div className="flex justify-between text-[9px] font-mono text-gray-600 px-1">
        <span>最小 <span className="text-clinical-cyan">{stats.min.toFixed(2)}</span></span>
        <span>平均 <span className="text-clinical-cyan">{stats.avg.toFixed(2)}</span></span>
        <span>最大 <span className="text-clinical-cyan">{stats.max.toFixed(2)}</span></span>
      </div>
    </div>
  );
}
