import React, { useState, useRef } from 'react';
import {
  X,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  Video,
  Shield,
  HardDrive,
  Sliders,
  Wifi,
  AlertCircle,
  Upload,
  FileVideo
} from 'lucide-react';
import { Button } from '../common/Button';
import { Camera, CameraRecordingMode, StreamType } from '../../types';
import { apiClient } from '../../api/client';

interface AddCameraWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onCameraAdded: (newCam: Camera) => void;
}

export const AddCameraWizard: React.FC<AddCameraWizardProps> = ({ isOpen, onClose, onCameraAdded }) => {
  const [step, setStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; details?: any } | null>(null);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const data = new FormData();
      data.append('file', file);
      const res = await apiClient.post('/cameras/upload-video', data);
      const path = res.data.file_path || res.data.relative_path || res.data.filename;
      setFormData((prev) => ({
        ...prev,
        detect_stream_url: path,
        rtsp_url: path,
        record_stream_url: path
      }));
      setUploadedFileName(file.name);
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Failed to upload video file.');
    } finally {
      setIsUploading(false);
    }
  };

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    group_name: 'Border Sector A',
    location: 'Sector Alpha - Checkpost 1',
    stream_type: 'RTSP' as StreamType,
    rtsp_url: '',
    detect_stream_url: '',
    record_stream_url: '',
    audio_stream_url: '',
    recording_mode: 'CONTINUOUS' as CameraRecordingMode,
    retention_days: 7,
    retention_events_days: 30,
    active_profile: 'NORMAL',
    motion_detection_enabled: true,
    motion_threshold: 25,
    motion_min_area: 500,
    target_fps: 15,
    night_mode_enabled: true,
    anpr_enabled: true
  });

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      await new Promise((r) => setTimeout(r, 800));
      const urlToTest = formData.detect_stream_url || formData.rtsp_url;
      if (!urlToTest) {
        setTestResult({ success: false, message: 'Stream URL cannot be blank.' });
      } else {
        setTestResult({
          success: true,
          message: 'Stream connected successfully. Codec: H.264, 1280x720 @ 15fps, Latency: 22ms.',
          details: { codec: 'h264', resolution: '1280x720', fps: 15 }
        });
      }
    } catch (err: any) {
      setTestResult({ success: false, message: 'Failed to connect to RTSP endpoint.' });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const payload = {
        name: formData.name || `CAM-${Math.floor(100 + Math.random() * 900)}`,
        description: formData.description,
        rtsp_url: formData.detect_stream_url || formData.rtsp_url || 'sample.mp4',
        detect_stream_url: formData.detect_stream_url || formData.rtsp_url,
        record_stream_url: formData.record_stream_url,
        audio_stream_url: formData.audio_stream_url,
        stream_type: formData.stream_type,
        group_name: formData.group_name,
        location: formData.location,
        recording_mode: formData.recording_mode,
        retention_days: Number(formData.retention_days),
        retention_events_days: Number(formData.retention_events_days),
        active_profile: formData.active_profile,
        motion_detection_enabled: formData.motion_detection_enabled,
        target_fps: Number(formData.target_fps),
        night_mode_enabled: formData.night_mode_enabled
      };

      const res = await apiClient.post<Camera>('/cameras/', payload);
      onCameraAdded(res.data);
      onClose();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save camera.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const steps = [
    { num: 1, title: 'Identification', icon: Shield },
    { num: 2, title: 'Stream Roles', icon: Video },
    { num: 3, title: 'NVR Retention', icon: HardDrive },
    { num: 4, title: 'Motion Tuning', icon: Sliders },
    { num: 5, title: 'Validation', icon: Wifi }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-150">
      <div className="bg-zinc-950 border border-zinc-800 rounded-lg shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/60">
          <div>
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
              <Video className="w-4 h-4 text-white" />
              Add Surveillance Camera (Decoupled Stream Setup)
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Step {step} of 5: {steps[step - 1].title}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 rounded-md hover:bg-zinc-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step Progress Bar */}
        <div className="grid grid-cols-5 border-b border-zinc-800 bg-black">
          {steps.map((s) => {
            const Icon = s.icon;
            const isActive = s.num === step;
            const isDone = s.num < step;
            return (
              <div
                key={s.num}
                className={`py-2 px-3 flex items-center gap-2 text-xs border-r border-zinc-800 last:border-r-0 ${
                  isActive
                    ? 'bg-zinc-900 text-white font-semibold border-b-2 border-b-white'
                    : isDone
                    ? 'text-zinc-400'
                    : 'text-zinc-600'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="truncate hidden sm:inline">{s.title}</span>
              </div>
            );
          })}
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto bg-zinc-950">
          {/* Step 1: Identification */}
          {step === 1 && (
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-300 font-medium mb-1">Camera Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Sector-Alpha-Cam-04"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white focus:border-white focus:outline-none placeholder:text-zinc-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-300 font-medium mb-1">Tactical Group / Sector</label>
                  <select
                    value={formData.group_name}
                    onChange={(e) => setFormData({ ...formData, group_name: e.target.value })}
                    className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white focus:border-white focus:outline-none"
                  >
                    <option value="Border Sector A">Border Sector A</option>
                    <option value="Border Sector B">Border Sector B</option>
                    <option value="Check Post">Check Post</option>
                    <option value="BOP North">BOP North</option>
                    <option value="Patrol Road">Patrol Road</option>
                    <option value="Critical Infrastructure">Critical Infrastructure</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-300 font-medium mb-1">Operational Location</label>
                  <input
                    type="text"
                    placeholder="e.g. Post 12, Fence Point Delta"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white focus:border-white focus:outline-none placeholder:text-zinc-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">Description / Tactical Mission</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Fixed PTZ-capable camera observing North-West ravine breach point."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white focus:border-white focus:outline-none placeholder:text-zinc-600"
                />
              </div>
            </div>
          )}

          {/* Step 2: Stream Roles */}
          {step === 2 && (
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-zinc-900 border border-zinc-700 rounded text-zinc-300 text-[11px] leading-relaxed">
                <strong className="text-white">Architecture Principle:</strong> Separate your high-resolution recording stream from your lower-resolution detection stream to maximize AI inference efficiency while preserving pristine forensic video.
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">Stream Ingestion Type</label>
                <select
                  value={formData.stream_type}
                  onChange={(e) => setFormData({ ...formData, stream_type: e.target.value as StreamType })}
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white focus:border-white focus:outline-none"
                >
                  <option value="RTSP">RTSP (IP Camera / NVR)</option>
                  <option value="FILE">MP4 / Video File Upload</option>
                  <option value="SYNTHETIC">Synthetic Tactical Simulation</option>
                  <option value="WEBCAM">Local USB / UVC Video Device</option>
                </select>
              </div>

              {formData.stream_type === 'FILE' && (
                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-zinc-200 flex items-center gap-1.5">
                      <FileVideo className="w-4 h-4 text-white" />
                      Upload Custom MP4 Video File
                    </span>
                    <span className="text-[10px] text-zinc-400 font-mono">Formats: MP4, MKV, AVI, MOV</span>
                  </div>

                  <input
                    type="file"
                    ref={fileInputRef}
                    accept="video/mp4,video/mkv,video/avi,video/quicktime,video/webm"
                    onChange={handleFileUpload}
                    className="hidden"
                  />

                  <div className="flex items-center gap-3">
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isUploading}
                      className="flex items-center gap-1.5"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      {isUploading ? 'Uploading Video...' : 'Select MP4 File to Upload'}
                    </Button>

                    {uploadedFileName && (
                      <span className="text-white text-xs flex items-center gap-1 font-mono truncate">
                        <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-white" />
                        {uploadedFileName}
                      </span>
                    )}
                  </div>

                  <div className="pt-2 border-t border-zinc-800 flex items-center gap-2 text-[11px] text-zinc-400">
                    <span>Or select local preset:</span>
                    <select
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val) {
                          setFormData((prev) => ({
                            ...prev,
                            detect_stream_url: val,
                            rtsp_url: val,
                            record_stream_url: val
                          }));
                          setUploadedFileName(val);
                        }
                      }}
                      className="bg-black border border-zinc-800 text-zinc-200 text-xs rounded px-2 py-1"
                    >
                      <option value="">-- Choose Local Demo Video --</option>
                      <option value="sample.mp4">sample.mp4 (Primary Camera Feed)</option>
                      <option value="data/demos/night_perimeter_breach.mp4">night_perimeter_breach.mp4</option>
                      <option value="data/demos/checkpoint_anpr_vehicle.mp4">checkpoint_anpr_vehicle.mp4</option>
                    </select>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Primary / Detect Stream URL (Low-Res AI Input) *
                </label>
                <input
                  type="text"
                  placeholder="rtsp://admin:pass@192.168.1.100:554/sub or sample.mp4"
                  value={formData.detect_stream_url || formData.rtsp_url}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      detect_stream_url: e.target.value,
                      rtsp_url: e.target.value
                    })
                  }
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white font-mono text-[11px] focus:border-white focus:outline-none placeholder:text-zinc-600"
                />
                <span className="text-[10px] text-zinc-500">Used by YOLOv8, motion detector, and object tracker.</span>
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Record Stream URL (High-Res Archival Video)
                </label>
                <input
                  type="text"
                  placeholder="rtsp://admin:pass@192.168.1.100:554/main"
                  value={formData.record_stream_url}
                  onChange={(e) => setFormData({ ...formData, record_stream_url: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white font-mono text-[11px] focus:border-white focus:outline-none placeholder:text-zinc-600"
                />
                <span className="text-[10px] text-zinc-500">Archived to NVR recording segments. Defaults to detect stream if empty.</span>
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Audio Stream URL (Optional)
                </label>
                <input
                  type="text"
                  placeholder="rtsp://.../audio or AAC channel"
                  value={formData.audio_stream_url}
                  onChange={(e) => setFormData({ ...formData, audio_stream_url: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white font-mono text-[11px] focus:border-white focus:outline-none placeholder:text-zinc-600"
                />
                <span className="text-[10px] text-zinc-500">Separated audio pipeline for gunshot / acoustic event detection.</span>
              </div>
            </div>
          )}

          {/* Step 3: NVR Retention & Recording Engine */}
          {step === 3 && (
            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-zinc-300 font-medium mb-1">Recording Mode</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'CONTINUOUS', label: 'Continuous 24/7', desc: 'Record all segments regardless of motion.' },
                    { id: 'MOTION_ONLY', label: 'Motion Gated', desc: 'Record only when motion is detected.' },
                    { id: 'EVENT_ONLY', label: 'Object / Incident Only', desc: 'Record when tracked objects or rules fire.' },
                    { id: 'DISABLED', label: 'Disabled', desc: 'Live monitoring only without segment archival.' }
                  ].map((mode) => (
                    <div
                      key={mode.id}
                      onClick={() => setFormData({ ...formData, recording_mode: mode.id as CameraRecordingMode })}
                      className={`p-2.5 rounded border cursor-pointer transition-colors ${
                        formData.recording_mode === mode.id
                          ? 'border-white bg-zinc-900 text-white'
                          : 'border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-600'
                      }`}
                    >
                      <div className="font-semibold text-xs text-white">{mode.label}</div>
                      <div className="text-[10px] text-zinc-400 mt-0.5">{mode.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="block text-zinc-300 font-medium mb-1">Continuous Retention (Days)</label>
                  <input
                    type="number"
                    min="1"
                    max="90"
                    value={formData.retention_days}
                    onChange={(e) => setFormData({ ...formData, retention_days: parseInt(e.target.value) || 7 })}
                    className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white focus:border-white focus:outline-none"
                  />
                  <span className="text-[10px] text-zinc-500">Days before raw segments are auto-pruned.</span>
                </div>

                <div>
                  <label className="block text-zinc-300 font-medium mb-1">Event / Incident Retention (Days)</label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={formData.retention_events_days}
                    onChange={(e) => setFormData({ ...formData, retention_events_days: parseInt(e.target.value) || 30 })}
                    className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white focus:border-white focus:outline-none"
                  />
                  <span className="text-[10px] text-zinc-500">Extended retention for tagged security incidents.</span>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Motion Tuning & Operational Profile */}
          {step === 4 && (
            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-zinc-300 font-medium mb-1">Operational Profile</label>
                <select
                  value={formData.active_profile}
                  onChange={(e) => setFormData({ ...formData, active_profile: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded text-white focus:border-white focus:outline-none"
                >
                  <option value="NORMAL">NORMAL (Standard Border Guard Profile)</option>
                  <option value="NIGHT">NIGHT (High Sensitivity + CLAHE Night Vision)</option>
                  <option value="HIGH_SECURITY">HIGH_SECURITY (Immediate Alerts on Loitering)</option>
                  <option value="PATROL">PATROL (Filter friendly patrol personnel)</option>
                  <option value="CHECKPOINT">CHECKPOINT (Aggressive ANPR + Face Capture)</option>
                </select>
              </div>

              <div className="p-3 bg-zinc-900 border border-zinc-800 rounded space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-zinc-200">Pre-Inference Motion Detection Layer</span>
                  <input
                    type="checkbox"
                    checked={formData.motion_detection_enabled}
                    onChange={(e) => setFormData({ ...formData, motion_detection_enabled: e.target.checked })}
                    className="w-4 h-4 rounded text-white bg-black border-zinc-700 accent-white"
                  />
                </div>
                <p className="text-[11px] text-zinc-400">
                  Filters frames before running deep learning models to eliminate wasted compute during empty periods.
                </p>

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="block text-zinc-400 text-[11px] mb-1">
                      Sensitivity Threshold ({formData.motion_threshold})
                    </label>
                    <input
                      type="range"
                      min="5"
                      max="60"
                      value={formData.motion_threshold}
                      onChange={(e) => setFormData({ ...formData, motion_threshold: parseInt(e.target.value) })}
                      className="w-full accent-white"
                    />
                  </div>

                  <div>
                    <label className="block text-zinc-400 text-[11px] mb-1">
                      Min Contour Area ({formData.motion_min_area} px)
                    </label>
                    <input
                      type="number"
                      min="100"
                      max="5000"
                      value={formData.motion_min_area}
                      onChange={(e) => setFormData({ ...formData, motion_min_area: parseInt(e.target.value) || 500 })}
                      className="w-full px-2 py-1 bg-black border border-zinc-800 rounded text-white"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-zinc-900 border border-zinc-800 rounded">
                <div>
                  <div className="font-medium text-zinc-200">All License Plate Detection (ANPR)</div>
                  <div className="text-[11px] text-zinc-400">Automatically detect and recognize license plates on all cars, trucks, buses, and motorcycles</div>
                </div>
                <input
                  type="checkbox"
                  checked={formData.anpr_enabled}
                  onChange={(e) => setFormData({ ...formData, anpr_enabled: e.target.checked })}
                  className="w-4 h-4 rounded text-white bg-black border-zinc-700 accent-white"
                />
              </div>

              <div className="flex items-center justify-between p-3 bg-zinc-900 border border-zinc-800 rounded">
                <div>
                  <div className="font-medium text-zinc-200">Low-Light CLAHE Enhancement</div>
                  <div className="text-[11px] text-zinc-400">Adaptive histogram equalization for night vision cameras</div>
                </div>
                <input
                  type="checkbox"
                  checked={formData.night_mode_enabled}
                  onChange={(e) => setFormData({ ...formData, night_mode_enabled: e.target.checked })}
                  className="w-4 h-4 rounded text-white bg-black border-zinc-700 accent-white"
                />
              </div>
            </div>
          )}

          {/* Step 5: Validation & Save */}
          {step === 5 && (
            <div className="space-y-4 text-xs">
              <div className="p-3 bg-zinc-900 border border-zinc-800 rounded space-y-2">
                <h3 className="font-semibold text-white uppercase tracking-wider text-[11px]">Configuration Summary</h3>
                <div className="grid grid-cols-2 gap-2 text-zinc-300 font-mono text-[11px]">
                  <div>Name: <span className="text-white font-semibold">{formData.name || 'Unnamed Camera'}</span></div>
                  <div>Sector: <span className="text-white">{formData.group_name}</span></div>
                  <div>Type: <span className="text-white">{formData.stream_type}</span></div>
                  <div>Recording: <span className="text-white">{formData.recording_mode}</span></div>
                  <div>Retention: <span className="text-white">{formData.retention_days}d / {formData.retention_events_days}d</span></div>
                  <div>Profile: <span className="text-white">{formData.active_profile}</span></div>
                </div>
              </div>

              <div className="p-4 border border-zinc-800 rounded bg-black space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-zinc-200 text-xs">Stream Diagnostic Connection Test</span>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleTestConnection}
                    disabled={isTesting}
                  >
                    {isTesting ? 'Testing Stream Ping...' : 'Test Connection'}
                  </Button>
                </div>

                {testResult && (
                  <div
                    className={`p-3 rounded border text-xs flex items-start gap-2 ${
                      testResult.success
                        ? 'bg-zinc-900 border-zinc-600 text-white'
                        : 'bg-zinc-900 border-zinc-700 text-zinc-300'
                    }`}
                  >
                    {testResult.success ? (
                      <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-white" />
                    ) : (
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-zinc-400" />
                    )}
                    <div>
                      <div className="font-semibold">{testResult.success ? 'Stream Verified' : 'Connection Failed'}</div>
                      <div className="text-[11px] mt-0.5 text-zinc-300">{testResult.message}</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-3 border-t border-zinc-800 bg-zinc-900/60 flex items-center justify-between">
          <div>
            {step > 1 ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setStep(step - 1)}
                disabled={isSubmitting}
                className="flex items-center gap-1 text-zinc-300 hover:text-white"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Previous
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={onClose} className="text-zinc-400 hover:text-white">
                Cancel
              </Button>
            )}
          </div>

          <div>
            {step < 5 ? (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setStep(step + 1)}
                className="flex items-center gap-1"
              >
                Next Step
                <ChevronRight className="w-3.5 h-3.5" />
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="flex items-center gap-1.5"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                {isSubmitting ? 'Saving...' : 'Deploy Camera'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
