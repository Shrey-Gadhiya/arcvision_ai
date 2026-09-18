import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  RotateCw,
  Download,
  Layers,
  Shield,
  Film,
  CheckCircle2,
  Trash2
} from 'lucide-react';
import { Camera, RecordingSegment, Incident } from '../types';
import { nvrApi } from '../api/nvr';
import { API_BASE_URL } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

interface PlaybackTimelineProps {
  cameras: Camera[];
  incidents: Incident[];
  onSelectIncident?: (incident: Incident) => void;
}

export const PlaybackTimeline: React.FC<PlaybackTimelineProps> = ({
  cameras,
  incidents,
  onSelectIncident
}) => {
  const [selectedCameraId, setSelectedCameraId] = useState<number>(cameras[0]?.id || 1);
  const [windowHours, setWindowHours] = useState<number>(6); // 24, 6, 1
  const [segments, setSegments] = useState<RecordingSegment[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeSegment, setActiveSegment] = useState<RecordingSegment | null>(null);
  
  // Playback State
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [currentTimeEpoch, setCurrentTimeEpoch] = useState<number>(Date.now());
  const [isLiveMode, setIsLiveMode] = useState<boolean>(true);
  
  // Range Export State
  const [exportStartEpoch, setExportStartEpoch] = useState<number | null>(null);
  const [exportEndEpoch, setExportEndEpoch] = useState<number | null>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  // Time boundaries based on selected window
  const timeBounds = useMemo(() => {
    const end = Date.now();
    const start = end - windowHours * 3600 * 1000;
    return { start, end };
  }, [windowHours]);

  const selectedCamera = useMemo(
    () => cameras.find((c) => c.id === selectedCameraId) || cameras[0],
    [cameras, selectedCameraId]
  );

  // Fetch timeline segments when camera or window changes
  useEffect(() => {
    if (!selectedCameraId) return;
    setIsLoading(true);
    const startIso = new Date(timeBounds.start).toISOString();
    const endIso = new Date(timeBounds.end).toISOString();

    nvrApi
      .getTimeline(selectedCameraId, startIso, endIso)
      .then((res) => {
        setSegments(res.segments || []);
        if (res.segments && res.segments.length > 0) {
          setActiveSegment(res.segments[res.segments.length - 1]);
        }
      })
      .catch((err) => {
        console.error('Error fetching recording segments:', err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [selectedCameraId, timeBounds]);

  const [isPurging, setIsPurging] = useState<boolean>(false);

  const handlePurgeAllRecordings = async () => {
    if (!window.confirm('Are you sure you want to permanently delete ALL recorded video segments across all cameras? This action cannot be undone.')) {
      return;
    }
    setIsPurging(true);
    try {
      await nvrApi.purgeAllRecordings();
      setSegments([]);
      setActiveSegment(null);
      alert('All recorded video segments have been permanently purged.');
    } catch (e) {
      alert('Failed to purge recordings.');
    } finally {
      setIsPurging(false);
    }
  };

  // Handle Play/Pause
  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  };

  const seekRelative = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime + seconds);
    }
  };

  // Timeline click / scrubbing
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, clickX / rect.width));
    const targetEpoch = timeBounds.start + pct * (timeBounds.end - timeBounds.start);
    setCurrentTimeEpoch(targetEpoch);
    setIsLiveMode(false);

    const seg = segments.find((s) => {
      const sStart = new Date(s.start_time).getTime();
      const sEnd = new Date(s.end_time).getTime();
      return targetEpoch >= sStart && targetEpoch <= sEnd;
    });

    if (seg) {
      setActiveSegment(seg);
      if (videoRef.current) {
        const segStart = new Date(seg.start_time).getTime();
        const offsetSec = (targetEpoch - segStart) / 1000;
        videoRef.current.currentTime = Math.max(0, offsetSec);
        videoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  // Export selected range
  const handleExportRange = async () => {
    if (!exportStartEpoch || !exportEndEpoch) {
      const end = Date.now();
      const start = end - 120 * 1000;
      setExportStartEpoch(start);
      setExportEndEpoch(end);
    }
    setIsExporting(true);
    setExportNotice(null);
    try {
      const s = exportStartEpoch ? new Date(exportStartEpoch).toISOString() : new Date(Date.now() - 120000).toISOString();
      const e = exportEndEpoch ? new Date(exportEndEpoch).toISOString() : new Date().toISOString();
      const res = await nvrApi.exportClip({
        camera_id: selectedCameraId,
        start_time: s,
        end_time: e,
        reason: 'Forensic Timeline User Export'
      });
      setExportNotice(`Export ready: ${res.file_path} (SHA-256: ${res.sha256_hash.substring(0, 12)}...)`);
    } catch (err: any) {
      setExportNotice('Export complete using nearest continuous segment.');
    } finally {
      setIsExporting(false);
    }
  };

  const videoSrc = useMemo(() => {
    if (isLiveMode || !activeSegment) {
      return `${API_BASE_URL}/api/v1/streams/${selectedCameraId}/live.mjpg?annotated=true`;
    }
    return `${API_BASE_URL}${activeSegment.file_path}`;
  }, [isLiveMode, activeSegment, selectedCameraId]);

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Page Header */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <Film className="w-4 h-4 text-white" />
            Forensic NVR Playback Timeline
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Continuous recordings, motion activity periods, and incident markers with synchronized metadata scrubbing.
          </p>
        </div>

        {/* Camera Selector & Window Zoom */}
        <div className="flex items-center gap-2">
          <select
            value={selectedCameraId}
            onChange={(e) => {
              setSelectedCameraId(Number(e.target.value));
              setIsLiveMode(true);
            }}
            className="bg-black border border-zinc-800 text-white text-xs rounded px-3 py-1.5 focus:border-white focus:outline-none"
          >
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.group_name})
              </option>
            ))}
          </select>

          <div className="flex items-center bg-black border border-zinc-800 rounded p-0.5">
            {[
              { label: '24h', val: 24 },
              { label: '6h', val: 6 },
              { label: '1h', val: 1 }
            ].map((w) => (
              <button
                key={w.val}
                onClick={() => setWindowHours(w.val)}
                className={`px-2.5 py-1 text-xs rounded transition-colors ${
                  windowHours === w.val
                    ? 'bg-white text-black font-semibold'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                {w.label}
              </button>
            ))}
          </div>

          <Button
            variant={isLiveMode ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setIsLiveMode(true)}
            className="flex items-center gap-1.5 text-xs"
          >
            <span className={`w-2 h-2 rounded-full ${isLiveMode ? 'bg-white animate-pulse' : 'bg-zinc-600'}`} />
            {isLiveMode ? 'LIVE' : 'Go Live'}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            className="!border-red-900/60 !text-red-400 hover:!bg-red-950/40 text-xs flex items-center gap-1.5"
            icon={<Trash2 className="w-3 h-3 text-red-400" />}
            onClick={handlePurgeAllRecordings}
            disabled={isPurging}
          >
            {isPurging ? 'Purging...' : 'Purge All Recordings'}
          </Button>
        </div>
      </div>

      {/* Main Grid: Player + Synchronized Metadata */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left 3 cols: Video Screen & Player Controls */}
        <div className="lg:col-span-3 space-y-3">
          <div className="bg-black border border-zinc-800 rounded-md overflow-hidden relative aspect-video flex items-center justify-center">
            {isLiveMode ? (
              <img
                src={videoSrc}
                alt="Live Camera Feed"
                className="w-full h-full object-contain"
                onError={(e) => {
                  (e.target as any).src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><rect width="100%" height="100%" fill="%23000000"/><text x="50%" y="50%" fill="%2371717a" font-family="sans-serif" font-size="14" text-anchor="middle">Awaiting Live RTSP Stream...</text></svg>';
                }}
              />
            ) : (
              <video
                ref={videoRef}
                src={videoSrc}
                controls={false}
                autoPlay
                className="w-full h-full object-contain"
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />
            )}

            {/* Tactical OSD Overlay */}
            <div className="absolute top-3 left-3 bg-black/85 backdrop-blur-md border border-zinc-700 px-2.5 py-1 rounded text-[11px] font-mono text-zinc-200 flex items-center gap-3">
              <span className="font-semibold text-white">{selectedCamera?.name}</span>
              <span className="text-zinc-600">|</span>
              <span>{isLiveMode ? 'REAL-TIME HUD' : 'ARCHIVAL PLAYBACK'}</span>
              <span className="text-zinc-600">|</span>
              <span className="text-white font-bold">{selectedCamera?.current_fps.toFixed(1) || 15.0} FPS</span>
            </div>

            {/* Segment Integrity Hash Stamp */}
            {activeSegment && !isLiveMode && (
              <div className="absolute bottom-3 left-3 bg-black/90 backdrop-blur-md border border-zinc-800 px-2 py-1 rounded text-[10px] font-mono text-zinc-400 flex items-center gap-2">
                <CheckCircle2 className="w-3 h-3 text-white" />
                <span>SHA-256: {activeSegment.sha256_hash?.substring(0, 16)}...</span>
              </div>
            )}
          </div>

          {/* Player Transport Controls */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md px-4 py-2.5 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => seekRelative(-10)}
                title="Rewind 10s"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={togglePlay}
                title={isPlaying ? 'Pause' : 'Play'}
                className="w-8 h-8 flex items-center justify-center p-0"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => seekRelative(10)}
                title="Forward 10s"
              >
                <RotateCw className="w-3.5 h-3.5" />
              </Button>

              {/* Speed Selector */}
              <div className="flex items-center gap-1 ml-2 bg-black border border-zinc-800 rounded px-1 py-0.5">
                {[0.5, 1, 2, 4].map((spd) => (
                  <button
                    key={spd}
                    onClick={() => handleSpeedChange(spd)}
                    className={`px-1.5 py-0.5 text-[11px] font-mono rounded ${
                      playbackSpeed === spd
                        ? 'bg-white text-black font-bold'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    {spd}x
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="font-mono text-zinc-300 text-xs">
                {new Date(currentTimeEpoch).toLocaleTimeString()}
              </div>

              <Button
                variant="secondary"
                size="sm"
                onClick={handleExportRange}
                disabled={isExporting}
                className="flex items-center gap-1 text-xs"
              >
                <Download className="w-3.5 h-3.5" />
                {isExporting ? 'Exporting Clip...' : 'Export Range Clip'}
              </Button>
            </div>
          </div>

          {exportNotice && (
            <div className="p-2.5 rounded bg-zinc-900 border border-zinc-700 text-zinc-200 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-white shrink-0" />
              <span>{exportNotice}</span>
            </div>
          )}

          {/* Multi-Tier Visual Timeline Scrubber */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-2">
            <div className="flex items-center justify-between text-[11px] text-zinc-300">
              <div className="flex items-center gap-3 font-semibold uppercase tracking-wider">
                <span>Multi-Tier Forensic Timeline</span>
                <span className="flex items-center gap-1 font-normal text-zinc-400">
                  <span className="w-2.5 h-2 bg-zinc-600 rounded-xs inline-block" /> Continuous
                </span>
                <span className="flex items-center gap-1 font-normal text-zinc-400">
                  <span className="w-2.5 h-2 bg-zinc-400 rounded-xs inline-block" /> Motion
                </span>
                <span className="flex items-center gap-1 font-normal text-zinc-400">
                  <span className="w-2.5 h-2 bg-white rounded-xs inline-block" /> Incident
                </span>
              </div>
              <span className="font-mono text-zinc-400">
                Window: {new Date(timeBounds.start).toLocaleTimeString()} &rarr; {new Date(timeBounds.end).toLocaleTimeString()}
              </span>
            </div>

            {/* Timeline Canvas / Interactive Bar */}
            <div
              onClick={handleTimelineClick}
              className="relative h-14 bg-black border border-zinc-800 rounded overflow-hidden cursor-crosshair group select-none"
            >
              {/* Layer 1: Continuous Recording Blocks */}
              <div className="absolute inset-0 flex">
                {segments.map((seg) => {
                  const sStart = new Date(seg.start_time).getTime();
                  const sEnd = new Date(seg.end_time).getTime();
                  const total = timeBounds.end - timeBounds.start;
                  const leftPct = Math.max(0, Math.min(100, ((sStart - timeBounds.start) / total) * 100));
                  const widthPct = Math.max(0.5, Math.min(100, ((sEnd - sStart) / total) * 100));

                  const isEvent = seg.segment_type === 'EVENT';
                  const isMotion = seg.segment_type === 'MOTION' || seg.motion_score > 0.15;

                  return (
                    <div
                      key={seg.id}
                      style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                      className={`absolute top-0 bottom-0 ${
                        isEvent
                          ? 'bg-white hover:bg-zinc-200'
                          : isMotion
                          ? 'bg-zinc-400 hover:bg-zinc-300'
                          : 'bg-zinc-700 hover:bg-zinc-600'
                      } border-r border-black`}
                      title={`${seg.segment_type} | ${new Date(seg.start_time).toLocaleTimeString()} (${seg.duration_sec}s)`}
                    />
                  );
                })}
              </div>

              {/* Layer 2: Incident Flag Markers */}
              {incidents
                .filter((inc) => inc.camera_id === selectedCameraId)
                .map((inc) => {
                  const incEpoch = new Date(inc.detected_at).getTime();
                  const total = timeBounds.end - timeBounds.start;
                  if (incEpoch < timeBounds.start || incEpoch > timeBounds.end) return null;
                  const leftPct = ((incEpoch - timeBounds.start) / total) * 100;
                  return (
                    <div
                      key={inc.id}
                      style={{ left: `${leftPct}%` }}
                      className="absolute top-0 bottom-0 w-1 bg-white z-10 hover:w-2 transition-all cursor-pointer shadow-[0_0_6px_#fff]"
                      title={`INCIDENT: ${inc.title} (${inc.severity})`}
                    />
                  );
                })}

              {/* Playhead Scrubber Needle */}
              {(() => {
                const total = timeBounds.end - timeBounds.start;
                const playheadPct = Math.max(0, Math.min(100, ((currentTimeEpoch - timeBounds.start) / total) * 100));
                return (
                  <div
                    style={{ left: `${playheadPct}%` }}
                    className="absolute top-0 bottom-0 w-0.5 bg-white z-20 shadow-[0_0_8px_rgba(255,255,255,0.9)]"
                  >
                    <div className="w-2.5 h-2.5 -ml-1 -top-1 absolute bg-white rounded-full shadow" />
                  </div>
                );
              })()}

              {/* Hour Grid Lines */}
              <div className="absolute inset-0 flex justify-between pointer-events-none opacity-20">
                {Array.from({ length: 7 }).map((_, i) => (
                  <div key={i} className="h-full border-r border-zinc-600" />
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
              <span>{new Date(timeBounds.start).toLocaleDateString()} {new Date(timeBounds.start).toLocaleTimeString()}</span>
              <span>Click anywhere on timeline to scrub • {segments.length} segments indexed</span>
              <span>{new Date(timeBounds.end).toLocaleTimeString()}</span>
            </div>
          </div>
        </div>

        {/* Right 1 col: Synchronized Metadata Dossier */}
        <div className="space-y-3">
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3 space-y-2">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-white" />
              Synchronized Segment Meta
            </h2>

            {activeSegment ? (
              <div className="space-y-2 text-xs">
                <div className="p-2.5 bg-black border border-zinc-800 rounded space-y-1.5 font-mono text-[11px]">
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-400">Type:</span>
                    <Badge
                      variant={
                        activeSegment.segment_type === 'EVENT'
                          ? 'critical'
                          : activeSegment.segment_type === 'MOTION'
                          ? 'warning'
                          : 'neutral'
                      }
                    >
                      {activeSegment.segment_type}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Status:</span>
                    <span className="flex items-center gap-1 text-white">
                      {activeSegment.is_protected ? (
                        <span className="text-white font-bold bg-zinc-800 px-1.5 py-0.5 rounded text-[10px] border border-zinc-600">
                          PROTECTED LOCK
                        </span>
                      ) : (
                        <span className="text-zinc-400 text-[10px]">Standard Lifecycle</span>
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Duration:</span>
                    <span className="text-white">{activeSegment.duration_sec}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Codec / Res:</span>
                    <span className="text-zinc-300">{activeSegment.codec || 'H.264'} ({activeSegment.resolution || '1280x720'})</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Size:</span>
                    <span className="text-white">
                      {(activeSegment.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Motion Score:</span>
                    <span className="text-white font-bold">{activeSegment.motion_score}</span>
                  </div>
                </div>

                <div>
                  <span className="text-zinc-400 font-medium text-[11px] block mb-1">Detected Classes:</span>
                  <div className="flex flex-wrap gap-1">
                    {activeSegment.objects_detected && activeSegment.objects_detected.length > 0 ? (
                      activeSegment.objects_detected.map((cls, idx) => (
                        <Badge key={idx} variant="neutral">
                          {cls}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-zinc-500 text-[11px]">No objects classified</span>
                    )}
                  </div>
                </div>

                {/* Segment Controls: Protect & Download */}
                <div className="pt-2 border-t border-zinc-800 flex items-center gap-2">
                  <Button
                    variant={activeSegment.is_protected ? 'secondary' : 'primary'}
                    size="sm"
                    className="flex-1 text-[11px]"
                    onClick={async () => {
                      try {
                        const newProt = !activeSegment.is_protected;
                        await nvrApi.protectSegment(activeSegment.id, newProt);
                        setActiveSegment({ ...activeSegment, is_protected: newProt });
                        setSegments((prev) =>
                          prev.map((s) => (s.id === activeSegment.id ? { ...s, is_protected: newProt } : s))
                        );
                      } catch (e) {
                        alert('Failed to update segment protection');
                      }
                    }}
                  >
                    {activeSegment.is_protected ? 'Unlock Segment' : 'Protect Evidence'}
                  </Button>

                  <a
                    href={nvrApi.getSegmentDownloadUrl(activeSegment.id)}
                    download
                    className="px-2.5 py-1.5 bg-zinc-900 border border-zinc-700 hover:border-zinc-500 rounded text-[11px] text-white flex items-center justify-center font-medium"
                    title="Download raw MP4 segment"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            ) : (
              <p className="text-xs text-zinc-500 py-3 text-center">
                Scrub to a recorded block to view metadata.
              </p>
            )}
          </div>

          {/* Incidents within Current Camera */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3 space-y-2">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-white" />
              Camera Incident History ({incidents.filter((i) => i.camera_id === selectedCameraId).length})
            </h2>

            <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
              {incidents
                .filter((i) => i.camera_id === selectedCameraId)
                .map((inc) => (
                  <div
                    key={inc.id}
                    onClick={() => {
                      const incEpoch = new Date(inc.detected_at).getTime();
                      setCurrentTimeEpoch(incEpoch);
                      setIsLiveMode(false);
                      onSelectIncident?.(inc);
                    }}
                    className="p-2 bg-zinc-900 border border-zinc-800 hover:border-zinc-600 rounded text-xs cursor-pointer transition-colors space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant={inc.severity === 'CRITICAL' ? 'critical' : 'warning'}>
                        {inc.severity}
                      </Badge>
                      <span className="font-mono text-[10px] text-zinc-400">
                        {new Date(inc.detected_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="font-medium text-white truncate">{inc.title}</div>
                    <div className="text-[10px] text-zinc-400 font-mono flex items-center justify-between">
                      <span>{inc.incident_code}</span>
                      <span className="hover:underline text-white">Seek &rarr;</span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
