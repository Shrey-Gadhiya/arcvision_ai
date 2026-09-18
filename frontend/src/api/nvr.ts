import { apiClient, API_BASE_URL } from './client';
import { RecordingSegment, TrackedSnapshot, StorageTelemetry } from '../types';

export interface TimelineResponse {
  camera_id: number;
  query_window: {
    start: string;
    end: string;
  };
  segment_count: number;
  segments: RecordingSegment[];
}

export const nvrApi = {
  // Recordings & Timeline
  async getTimeline(
    cameraId: number,
    startTime?: string,
    endTime?: string,
    segmentType?: string
  ): Promise<TimelineResponse> {
    const params: Record<string, any> = {};
    if (startTime) params.start_time = startTime;
    if (endTime) params.end_time = endTime;
    if (segmentType) params.segment_type = segmentType;

    const res = await apiClient.get<TimelineResponse>(`/recordings/timeline/${cameraId}`, { params });
    return res.data;
  },

  getSegmentStreamUrl(segmentId: number): string {
    return `${API_BASE_URL}/api/v1/recordings/${segmentId}/stream`;
  },

  getSegmentDownloadUrl(segmentId: number): string {
    return `${API_BASE_URL}/api/v1/recordings/${segmentId}/download`;
  },

  async listRecordings(params?: {
    camera_id?: number;
    segment_type?: string;
    is_protected?: boolean;
    has_objects?: boolean;
    start_time?: string;
    end_time?: string;
    limit?: number;
    offset?: number;
  }) {
    const res = await apiClient.get('/recordings/', { params });
    return res.data;
  },

  async protectSegment(segmentId: number, isProtected: boolean = true, reason?: string) {
    const res = await apiClient.post(`/recordings/${segmentId}/protect`, {
      is_protected: isProtected,
      reason: reason || 'Forensic Investigation Lock'
    });
    return res.data;
  },

  async deleteSegment(segmentId: number) {
    const res = await apiClient.delete(`/recordings/${segmentId}`);
    return res.data;
  },

  async exportEvidencePackage(incidentId: number) {
    const res = await apiClient.post(`/evidence/export-package/${incidentId}`);
    return res.data;
  },

  async verifyEvidencePackage(packageFilename: string) {
    const res = await apiClient.post('/evidence/verify-package', {
      package_filename: packageFilename
    });
    return res.data;
  },

  async searchInvestigation(params: Record<string, any>) {
    const res = await apiClient.post('/investigation/search', params);
    return res.data;
  },

  async exportClip(payload: {
    camera_id: number;
    start_time: string;
    end_time: string;
    reason?: string;
  }) {
    const res = await apiClient.post('/recordings/export', payload);
    return res.data;
  },

  // Storage Manager & Retention
  async getStorageTelemetry(): Promise<StorageTelemetry> {
    const res = await apiClient.get<StorageTelemetry>('/recordings/storage/telemetry');
    return res.data;
  },

  async enforceRetention(): Promise<{ pruned_segments: number; freed_bytes: number; timestamp: string }> {
    const res = await apiClient.post('/recordings/storage/enforce-retention');
    return res.data;
  },

  // Snapshots & Review Feed
  async listSnapshots(params?: {
    camera_id?: number;
    object_class?: string;
    min_confidence?: number;
    limit?: number;
    offset?: number;
  }) {
    const res = await apiClient.get('/snapshots/', { params });
    return res.data;
  },

  async getRecentSnapshotFeed(cameraId?: number, limit?: number) {
    const params: Record<string, any> = {};
    if (cameraId) params.camera_id = cameraId;
    if (limit) params.limit = limit;
    const res = await apiClient.get('/snapshots/recent/feed', { params });
    return res.data;
  },
};

