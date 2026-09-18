import React, { useState, useEffect, useMemo } from 'react';
import {
  Eye,
  Play,
  Layers,
  LayoutGrid,
  List,
  Clock,
  Maximize2
} from 'lucide-react';
import { Camera, TrackedSnapshot } from '../types';
import { nvrApi } from '../api/nvr';
import { API_BASE_URL } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

interface ReviewStreamProps {
  cameras: Camera[];
  onOpenTimelineAt?: (cameraId: number, timestampIso: string) => void;
}

export const ReviewStream: React.FC<ReviewStreamProps> = ({ cameras, onOpenTimelineAt }) => {
  const [snapshots, setSnapshots] = useState<TrackedSnapshot[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedCameraId, setSelectedCameraId] = useState<number | 'ALL'>('ALL');
  const [selectedClass, setSelectedClass] = useState<string>('ALL');
  const [minConfidence] = useState<number>(0.3);
  const [aspectMode, setAspectMode] = useState<'portrait' | 'square' | 'feed'>('portrait');
  const [imageFit, setImageFit] = useState<'contain' | 'cover'>('contain');
  const [selectedModalSnap, setSelectedModalSnap] = useState<TrackedSnapshot | null>(null);
  const [modalViewMode, setModalViewMode] = useState<'crop' | 'annotated' | 'clean'>('crop');

  const fetchFeed = () => {
    setIsLoading(true);
    const camId = selectedCameraId === 'ALL' ? undefined : selectedCameraId;
    const objCls = selectedClass === 'ALL' ? undefined : selectedClass;

    nvrApi
      .listSnapshots({
        camera_id: camId,
        object_class: objCls,
        min_confidence: minConfidence,
        limit: 50
      })
      .then((res) => {
        setSnapshots(res.snapshots || []);
      })
      .catch((err) => {
        console.error('Failed to load review snapshots:', err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchFeed();
    const interval = setInterval(fetchFeed, 8000);
    return () => clearInterval(interval);
  }, [selectedCameraId, selectedClass, minConfidence]);

  const cameraMap = useMemo(() => {
    const map = new Map<number, Camera>();
    cameras.forEach((c) => map.set(c.id, c));
    return map;
  }, [cameras]);

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <Eye className="w-4 h-4 text-white" />
            Tracked Object Review & Fast Intelligence Stream
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Full uncropped vertical target review. Inspect complete head-to-toe persons and vehicles directly from the feed.
          </p>
        </div>

        {/* Controls and Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Aspect Ratio View Toggle */}
          <div className="flex items-center bg-black border border-zinc-800 rounded p-0.5 text-xs">
            <button
              onClick={() => setAspectMode('portrait')}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                aspectMode === 'portrait'
                  ? 'bg-white text-black font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
              title="Vertical 3:4 Portrait (Full Person View)"
            >
              <span className="text-[11px]">3:4 Vertical</span>
            </button>
            <button
              onClick={() => setAspectMode('square')}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                aspectMode === 'square'
                  ? 'bg-white text-black font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
              title="1:1 Square View"
            >
              <span className="text-[11px]">1:1 Square</span>
            </button>
            <button
              onClick={() => setAspectMode('feed')}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                aspectMode === 'feed'
                  ? 'bg-white text-black font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
              title="Vertical Feed Stream"
            >
              <List className="w-3.5 h-3.5" />
              <span className="text-[11px] hidden sm:inline">Feed</span>
            </button>
          </div>

          {/* Fit Mode Toggle */}
          <div className="flex items-center bg-black border border-zinc-800 rounded p-0.5 text-xs">
            <button
              onClick={() => setImageFit('contain')}
              className={`px-2 py-1 rounded text-[11px] transition-colors ${
                imageFit === 'contain'
                  ? 'bg-zinc-800 text-white font-medium'
                  : 'text-zinc-400 hover:text-white'
              }`}
              title="Fit Full Object without any cropping"
            >
              Full Object (Fit)
            </button>
            <button
              onClick={() => setImageFit('cover')}
              className={`px-2 py-1 rounded text-[11px] transition-colors ${
                imageFit === 'cover'
                  ? 'bg-zinc-800 text-white font-medium'
                  : 'text-zinc-400 hover:text-white'
              }`}
              title="Fill entire container"
            >
              Fill Frame
            </button>
          </div>

          {/* Camera Filter */}
          <select
            value={selectedCameraId}
            onChange={(e) => setSelectedCameraId(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
            className="bg-black border border-zinc-800 text-white text-xs rounded px-2.5 py-1.5 focus:border-white focus:outline-none"
          >
            <option value="ALL">All Cameras ({cameras.length})</option>
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          {/* Object Class Filter */}
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            className="bg-black border border-zinc-800 text-white text-xs rounded px-2.5 py-1.5 focus:border-white focus:outline-none"
          >
            <option value="ALL">All Objects</option>
            <option value="person">Person</option>
            <option value="car">Vehicle / Car</option>
            <option value="truck">Truck</option>
            <option value="bus">Bus</option>
            <option value="motorcycle">Motorcycle</option>
          </select>

          <Button variant="secondary" size="sm" onClick={fetchFeed} className="text-xs">
            Refresh
          </Button>
        </div>
      </div>

      {/* Snapshots Content */}
      {isLoading && snapshots.length === 0 ? (
        <div className="p-12 text-center text-xs text-zinc-500 bg-zinc-950 border border-zinc-800 rounded-md">
          Loading object review stream...
        </div>
      ) : snapshots.length === 0 ? (
        <div className="p-12 text-center text-xs text-zinc-500 bg-zinc-950 border border-zinc-800 rounded-md space-y-2">
          <Eye className="w-8 h-8 text-zinc-600 mx-auto" />
          <p>No tracked object snapshots match current criteria.</p>
          <p className="text-[11px] text-zinc-600">Snapshots are automatically captured as camera feeds detect objects.</p>
        </div>
      ) : aspectMode === 'feed' ? (
        /* Vertical Detailed Feed List View */
        <div className="space-y-3 max-w-4xl mx-auto">
          {snapshots.map((snap) => {
            const cam = cameraMap.get(snap.camera_id);
            const imageSrc = `${API_BASE_URL}${snap.crop_image_path || snap.annotated_image_path}`;

            return (
              <div
                key={snap.id}
                className="bg-zinc-950 border border-zinc-800 hover:border-zinc-600 rounded-md p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all group"
              >
                {/* Left: Vertical Portrait Crop Box + Info */}
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {/* Vertical Portrait Container */}
                  <div
                    onClick={() => setSelectedModalSnap(snap)}
                    className="w-24 h-32 sm:w-28 sm:h-36 aspect-[3/4] bg-black rounded border border-zinc-800 overflow-hidden cursor-pointer shrink-0 relative group-hover:border-zinc-500 transition-colors flex items-center justify-center p-1"
                  >
                    <img
                      src={imageSrc}
                      alt={`${snap.object_class} crop`}
                      className={`w-full h-full ${imageFit === 'contain' ? 'object-contain' : 'object-cover'} group-hover:scale-105 transition-transform duration-200`}
                      onError={(e) => {
                        (e.target as any).src = `${API_BASE_URL}${snap.annotated_image_path}`;
                      }}
                    />
                    <div className="absolute bottom-1 right-1 bg-black/90 text-white text-[9px] font-mono px-1 rounded border border-zinc-700">
                      {Math.round(snap.confidence * 100)}%
                    </div>
                  </div>

                  {/* Metadata and Context */}
                  <div className="space-y-1.5 min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="neutral">
                        {snap.object_class.toUpperCase()} #{snap.track_id}
                      </Badge>
                      <span className="font-semibold text-white text-xs truncate">
                        {cam?.name || `Camera #${snap.camera_id}`}
                      </span>
                      <span className="text-[11px] text-zinc-500 font-mono">
                        {cam?.location || 'Sector Perimeter'}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-zinc-500" />
                        {new Date(snap.timestamp).toLocaleString()}
                      </span>
                      {snap.quality_score && (
                        <span>Quality: {snap.quality_score.toFixed(2)}</span>
                      )}
                    </div>

                    <p className="text-xs text-zinc-400 font-sans line-clamp-1">
                      Full vertical object detection captured at {new Date(snap.timestamp).toLocaleTimeString()}.
                    </p>
                  </div>
                </div>

                {/* Right: Instant Review Actions */}
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setSelectedModalSnap(snap)}
                    className="flex items-center gap-1 text-xs"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    Evidence
                  </Button>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => onOpenTimelineAt?.(snap.camera_id, snap.timestamp)}
                    className="flex items-center gap-1.5 text-xs"
                  >
                    <Play className="w-3.5 h-3.5" />
                    Timeline
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Vertical Portrait (3:4) or Square (1:1) Grid Cards */
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3.5">
          {snapshots.map((snap) => {
            const cam = cameraMap.get(snap.camera_id);
            const imageSrc = `${API_BASE_URL}${snap.crop_image_path || snap.annotated_image_path}`;

            return (
              <div
                key={snap.id}
                className="bg-zinc-950 border border-zinc-800 hover:border-zinc-500 rounded-md overflow-hidden transition-all flex flex-col group shadow-sm hover:shadow-md"
              >
                {/* Vertical Aspect Container (3:4 or 1:1) */}
                <div
                  onClick={() => setSelectedModalSnap(snap)}
                  className={`relative w-full ${
                    aspectMode === 'portrait' ? 'aspect-[3/4]' : 'aspect-square'
                  } bg-black overflow-hidden cursor-pointer flex items-center justify-center p-1.5 border-b border-zinc-900 select-none`}
                >
                  <img
                    src={imageSrc}
                    alt={`${snap.object_class} crop`}
                    className={`w-full h-full ${
                      imageFit === 'contain' ? 'object-contain' : 'object-cover'
                    } group-hover:scale-105 transition-transform duration-200`}
                    onError={(e) => {
                      (e.target as any).src = `${API_BASE_URL}${snap.annotated_image_path}`;
                    }}
                  />

                  {/* Class Badge Top-Left */}
                  <div className="absolute top-2 left-2 flex items-center gap-1 z-10">
                    <Badge variant="neutral">
                      {snap.object_class.toUpperCase()} #{snap.track_id}
                    </Badge>
                  </div>

                  {/* Confidence Badge Top-Right */}
                  <div className="absolute top-2 right-2 z-10">
                    <span className="bg-black/90 text-white text-[10px] font-mono px-1.5 py-0.5 rounded border border-zinc-700 shadow">
                      {Math.round(snap.confidence * 100)}%
                    </span>
                  </div>

                  {/* Quality Score Indicator Bottom-Right */}
                  {snap.quality_score && (
                    <div className="absolute bottom-2 right-2 bg-black/90 text-zinc-300 text-[10px] font-mono px-1.5 py-0.5 rounded border border-zinc-800 z-10">
                      Q: {snap.quality_score.toFixed(2)}
                    </div>
                  )}

                  {/* Hover Quick Action Overlay */}
                  <div className="absolute inset-0 bg-black/60 backdrop-blur-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 z-20">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenTimelineAt?.(snap.camera_id, snap.timestamp);
                      }}
                      className="px-3 py-1.5 rounded bg-white text-black font-semibold text-xs flex items-center gap-1 shadow hover:bg-zinc-200 transition-colors"
                    >
                      <Play className="w-3 h-3 fill-black" />
                      Play Timeline
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedModalSnap(snap);
                      }}
                      className="p-1.5 rounded bg-zinc-900 border border-zinc-700 text-white text-xs hover:bg-zinc-800 transition-colors"
                      title="Inspect Frame"
                    >
                      <Maximize2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Details Card Footer */}
                <div className="p-3 space-y-2 text-xs bg-zinc-950 flex-1 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-white font-medium">
                      <span className="truncate text-xs">{cam?.name || `Camera #${snap.camera_id}`}</span>
                      <span className="font-mono text-[10px] text-zinc-400">
                        {new Date(snap.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-[11px] text-zinc-400 truncate mt-0.5">
                      {cam?.location || 'Perimeter Sector'}
                    </div>
                  </div>

                  {/* Direct Action Bar on the Card */}
                  <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between gap-1.5">
                    <button
                      onClick={() => setSelectedModalSnap(snap)}
                      className="text-zinc-400 hover:text-white text-[11px] flex items-center gap-1"
                    >
                      <Layers className="w-3 h-3" />
                      Evidence
                    </button>

                    <Button
                      variant="primary"
                      size="xs"
                      onClick={() => onOpenTimelineAt?.(snap.camera_id, snap.timestamp)}
                      className="flex items-center gap-1 text-[11px] py-0.5 px-2"
                    >
                      <Play className="w-2.5 h-2.5" />
                      Timeline
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Snapshot Evidence Inspection Modal */}
      {selectedModalSnap && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-in fade-in duration-150">
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="px-5 py-3.5 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/60">
              <div>
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                  <Eye className="w-4 h-4 text-white" />
                  Tracked Object #{selectedModalSnap.track_id} — {selectedModalSnap.object_class.toUpperCase()}
                </h3>
                <span className="text-xs text-zinc-400 font-mono">
                  {new Date(selectedModalSnap.timestamp).toLocaleString()} • Confidence: {Math.round(selectedModalSnap.confidence * 100)}%
                </span>
              </div>

              {/* View Toggle */}
              <div className="flex items-center bg-black border border-zinc-800 rounded p-0.5 text-xs">
                {(['crop', 'annotated', 'clean'] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setModalViewMode(m)}
                    className={`px-3 py-1 rounded capitalize transition-colors ${
                      modalViewMode === m
                        ? 'bg-white text-black font-semibold'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    {m === 'crop' ? 'Full Crop' : m}
                  </button>
                ))}
              </div>
            </div>

            {/* Modal Image Display */}
            <div className="p-4 bg-black flex items-center justify-center max-h-[65vh] overflow-hidden">
              <img
                src={`${API_BASE_URL}${
                  modalViewMode === 'clean'
                    ? selectedModalSnap.clean_image_path
                    : modalViewMode === 'crop'
                    ? (selectedModalSnap.crop_image_path || selectedModalSnap.annotated_image_path)
                    : selectedModalSnap.annotated_image_path
                }`}
                alt="Representative frame"
                className="max-h-[60vh] max-w-full object-contain rounded"
              />
            </div>

            {/* Modal Footer */}
            <div className="px-5 py-3 border-t border-zinc-800 bg-zinc-900/60 flex items-center justify-between">
              <span className="text-xs font-mono text-zinc-400">
                High-Resolution Representative Frame
              </span>

              <div className="flex items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    onOpenTimelineAt?.(selectedModalSnap.camera_id, selectedModalSnap.timestamp);
                    setSelectedModalSnap(null);
                  }}
                  className="flex items-center gap-1.5"
                >
                  <Play className="w-3.5 h-3.5" />
                  Open in Forensic Timeline
                </Button>

                <Button variant="secondary" size="sm" onClick={() => setSelectedModalSnap(null)}>
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
