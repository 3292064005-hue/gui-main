import { useEffect, useState, useRef, useCallback } from 'react';
import { Radio, Maximize2, Download, XCircle } from 'lucide-react';
import { wsUrl } from '../api/config';

export default function UltrasoundFeed() {
  const [frame, setFrame] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [fps, setFps] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const fpsCountRef = useRef(0);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const iv = setInterval(() => {
      setFps(fpsCountRef.current);
      fpsCountRef.current = 0;
    }, 1000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(wsUrl('/ws/ultrasound'));
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onmessage = (event) => {
        setFrame(`data:image/png;base64,${event.data}`);
        fpsCountRef.current++;
      };
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => wsRef.current?.close();
  }, []);

  const snapshot = useCallback(() => {
    if (!imgRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = imgRef.current.naturalWidth || 640;
    canvas.height = imgRef.current.naturalHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx?.drawImage(imgRef.current, 0, 0);
    const a = document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = `ultrasound_${Date.now()}.png`;
    a.click();
  }, []);

  const containerClass = fullscreen
    ? 'fixed inset-0 z-[90] bg-black/95 flex flex-col items-center justify-center p-8'
    : 'glass-panel p-2 flex flex-col pointer-events-auto shadow-2xl mt-3 transition-all duration-300';

  const videoClass = fullscreen ? 'max-w-full max-h-[80vh] rounded-xl' : 'w-72 h-44';

  return (
    <div className={containerClass}>
      {/* Header */}
      <div className="flex items-center justify-between w-full mb-1.5 px-1">
        <h3 className="text-[10px] text-clinical-emerald font-bold tracking-widest uppercase flex items-center">
          <div className={`w-1.5 h-1.5 rounded-full mr-1.5 ${connected ? 'bg-clinical-emerald animate-pulse' : 'bg-clinical-error'}`} />
          超声 B-Mode
          <span className="text-gray-600 ml-2">{fps} FPS</span>
        </h3>
        <div className="flex space-x-1">
          <button onClick={snapshot} className="p-1 rounded hover:bg-white/10 transition-colors" title="截图">
            <Download className="w-3 h-3 text-gray-400" />
          </button>
          <button onClick={() => setFullscreen(!fullscreen)} className="p-1 rounded hover:bg-white/10 transition-colors" title="全屏">
            {fullscreen ? <XCircle className="w-3 h-3 text-gray-400" /> : <Maximize2 className="w-3 h-3 text-gray-400" />}
          </button>
        </div>
      </div>

      {/* Video Frame */}
      <div className={`relative ${videoClass} bg-black/80 rounded-lg overflow-hidden border border-white/5`}>
        {frame ? (
          <>
            <img ref={imgRef} src={frame} alt="US" className="w-full h-full object-cover" crossOrigin="anonymous" />
            {/* Scan line effect */}
            <div className="absolute inset-0 pointer-events-none">
              <div className="w-full h-[2px] bg-gradient-to-r from-transparent via-clinical-emerald/40 to-transparent animate-scanline" />
            </div>
          </>
        ) : (
          <div className="flex w-full h-full items-center justify-center text-gray-500 font-mono text-xs">
            <Radio className="w-5 h-5 mr-2 opacity-30" /> 探头离线
          </div>
        )}
      </div>
    </div>
  );
}
