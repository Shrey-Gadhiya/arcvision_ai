import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  Download,
  RefreshCw,
  Eye,
  Package,
  ShieldCheck,
  AlertTriangle,
  Lock,
  Film,
  Search,
  SlidersHorizontal,
  Copy,
  Check,
  Tag,
  Car,
  UserCheck,
  FileCheck2
} from 'lucide-react';
import { Evidence, EvidencePackageExportResponse, EvidencePackageVerifyResponse } from '../types';
import { apiClient, getMediaUrl } from '../api/client';
import { nvrApi } from '../api/nvr';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const EvidenceLocker: React.FC = () => {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [verifyingId, setVerifyingId] = useState<number | null>(null);
  const [verificationStatus, setVerificationStatus] = useState<Record<number, any>>({});
  const [previewItem, setPreviewItem] = useState<Evidence | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Filters & Search
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Batch Verification State
  const [isVerifyingAll, setIsVerifyingAll] = useState<boolean>(false);
  const [batchVerifySummary, setBatchVerifySummary] = useState<{
    total_checked: number;
    valid_count: number;
    tampered_count: number;
    tampered_items: any[];
  } | null>(null);

  // Package Export State
  const [exportIncidentId, setExportIncidentId] = useState<string>('1');
  const [isExportingPkg, setIsExportingPkg] = useState<boolean>(false);
  const [exportedPkg, setExportedPkg] = useState<EvidencePackageExportResponse | null>(null);

  // Package Verification State
  const [verifyPkgFilename, setVerifyPkgFilename] = useState<string>('');
  const [isVerifyingPkg, setIsVerifyingPkg] = useState<boolean>(false);
  const [pkgVerifyResult, setPkgVerifyResult] = useState<EvidencePackageVerifyResponse | null>(null);

  const fetchEvidence = async () => {
    try {
      const res = await apiClient.get('/evidence/');
      setEvidence(res.data);
    } catch (e) {
      console.error('Failed to fetch evidence:', e);
    }
  };

  useEffect(() => {
    fetchEvidence();
  }, []);

  const handleVerify = async (evId: number) => {
    setVerifyingId(evId);
    try {
      const res = await apiClient.post(`/evidence/${evId}/verify`);
      setVerificationStatus((prev) => ({ ...prev, [evId]: res.data }));
    } catch (e) {
      alert('Verification failed or file unreachable');
    } finally {
      setVerifyingId(null);
    }
  };

  const handleVerifyAll = async () => {
    setIsVerifyingAll(true);
    setBatchVerifySummary(null);
    try {
      const res = await apiClient.post('/evidence/verify-all');
      setBatchVerifySummary(res.data);
      // Update individual verified status
      if (res.data.results) {
        const newStatuses: Record<number, any> = {};
        for (const r of res.data.results) {
          newStatuses[r.evidence_id] = {
            is_valid: r.is_valid,
            file_exists: r.file_exists,
            calculated_sha256: r.calculated_sha256
          };
        }
        setVerificationStatus((prev) => ({ ...prev, ...newStatuses }));
      }
    } catch (err: any) {
      alert('Batch evidence verification failed');
    } finally {
      setIsVerifyingAll(false);
    }
  };

  const handleExportPackage = async () => {
    if (!exportIncidentId) return;
    setIsExportingPkg(true);
    setExportedPkg(null);
    try {
      const res = await nvrApi.exportEvidencePackage(Number(exportIncidentId));
      setExportedPkg(res);
      setVerifyPkgFilename(res.package_filename);
    } catch (err: any) {
      alert('Failed to export evidence package. Ensure incident exists and has records.');
    } finally {
      setIsExportingPkg(false);
    }
  };

  const handleVerifyPackage = async () => {
    if (!verifyPkgFilename) return;
    setIsVerifyingPkg(true);
    setPkgVerifyResult(null);
    try {
      const res = await nvrApi.verifyEvidencePackage(verifyPkgFilename);
      setPkgVerifyResult(res);
    } catch (err: any) {
      alert('Package verification failed or package file not found.');
    } finally {
      setIsVerifyingPkg(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Filter evidence list
  const filteredEvidence = evidence.filter((item) => {
    if (typeFilter !== 'ALL' && item.file_type !== typeFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = String(item.id).includes(q);
      const matchCam = String(item.camera_id).includes(q);
      const matchInc = item.incident_id ? String(item.incident_id).includes(q) : false;
      const matchHash = item.sha256_hash.toLowerCase().includes(q);
      const matchMeta = item.metadata_json.toLowerCase().includes(q);
      const matchType = item.file_type.toLowerCase().includes(q);
      return matchId || matchCam || matchInc || matchHash || matchMeta || matchType;
    }
    return true;
  });

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'CROP_PLATE':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
            <Car className="w-3 h-3" />
            PLATE CROP
          </span>
        );
      case 'CROP_FACE':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">
            <UserCheck className="w-3 h-3" />
            FACE CROP
          </span>
        );
      case 'CLIP':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-900 text-zinc-200 border border-zinc-700">
            <Film className="w-3 h-3" />
            VIDEO CLIP
          </span>
        );
      case 'SNAPSHOT':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-900 text-zinc-300 border border-zinc-800">
            <Tag className="w-3 h-3" />
            SNAPSHOT
          </span>
        );
      default:
        return (
          <Badge variant="neutral">
            {type}
          </Badge>
        );
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-full font-sans">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <Lock className="w-4 h-4 text-white" />
            Digital Evidence Repository & Tamper-Evident Locker
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Forensic video clips, high-resolution snapshots, facial & license plate crops with cryptographic SHA-256 chain of custody verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={<ShieldCheck className={`w-3.5 h-3.5 ${isVerifyingAll ? 'animate-spin' : ''}`} />}
            onClick={handleVerifyAll}
            disabled={isVerifyingAll}
          >
            {isVerifyingAll ? 'Auditing SHA-256 Hashes...' : 'Verify All Evidence'}
          </Button>

          <Button variant="secondary" size="sm" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchEvidence}>
            Refresh Repository
          </Button>
        </div>
      </div>

      {/* Batch Integrity Summary Banner */}
      {batchVerifySummary && (
        <div className="p-3 bg-zinc-900 border border-zinc-700 rounded text-xs flex flex-wrap items-center justify-between gap-3 font-mono">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-zinc-200">
              Audit Complete: <strong className="text-emerald-400">{batchVerifySummary.valid_count}</strong> of <strong>{batchVerifySummary.total_checked}</strong> files intact (100% Cryptographic Match).
            </span>
          </div>
          {batchVerifySummary.tampered_count > 0 && (
            <span className="text-red-400 font-bold">
              {batchVerifySummary.tampered_count} files tampered / missing!
            </span>
          )}
        </div>
      )}

      {/* Package Exporter & Package Verifier Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Box 1: Export Complete Incident Package */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3">
          <div className="flex items-center gap-2 border-b border-zinc-800 pb-2">
            <Package className="w-4 h-4 text-white" />
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
              Export Evidence Package (.ZIP)
            </h2>
          </div>

          <p className="text-[11px] text-zinc-400">
            Bundles incident report metadata, snapshot images, event video clip, and manifest.json with cryptographic SHA-256 checksums. Locks linked recordings.
          </p>

          <div className="flex items-center gap-2 text-xs">
            <input
              type="number"
              value={exportIncidentId}
              onChange={(e) => setExportIncidentId(e.target.value)}
              placeholder="Incident ID (e.g. 1)"
              className="bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white w-32 focus:outline-none focus:border-white font-mono text-xs"
            />
            <Button
              variant="primary"
              size="sm"
              onClick={handleExportPackage}
              disabled={isExportingPkg}
              className="text-xs"
            >
              {isExportingPkg ? 'Generating ZIP...' : 'Generate Evidence Package'}
            </Button>
          </div>

          {exportedPkg && (
            <div className="p-3 bg-zinc-900 border border-zinc-700 rounded text-xs space-y-2 font-mono text-zinc-200">
              <div className="flex items-center justify-between text-white font-bold">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-white" />
                  {exportedPkg.package_filename}
                </span>
                <span className="text-[10px] bg-zinc-800 border border-zinc-600 px-1.5 py-0.5 rounded">
                  PROTECTED
                </span>
              </div>
              <div className="text-[11px] text-zinc-400 break-all">
                SHA-256: <span className="text-zinc-200">{exportedPkg.sha256_hash}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span>Files Bundled: {exportedPkg.total_files}</span>
                <a
                  href={getMediaUrl(exportedPkg.download_url)}
                  download
                  className="px-2.5 py-1 bg-white text-black font-semibold rounded hover:bg-zinc-200 flex items-center gap-1 font-sans"
                >
                  <Download className="w-3 h-3" /> Download ZIP
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Box 2: Deep Package Cryptographic Verification */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3">
          <div className="flex items-center gap-2 border-b border-zinc-800 pb-2">
            <ShieldCheck className="w-4 h-4 text-white" />
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
              Cryptographic Package Verification
            </h2>
          </div>

          <p className="text-[11px] text-zinc-400">
            Recalculates SHA-256 for all zipped assets from physical disk and validates against the embedded manifest.json signature.
          </p>

          <div className="flex items-center gap-2 text-xs">
            <input
              type="text"
              value={verifyPkgFilename}
              onChange={(e) => setVerifyPkgFilename(e.target.value)}
              placeholder="e.g. evidence_package_INC-2026-001.zip"
              className="bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white flex-1 focus:outline-none focus:border-white font-mono text-xs"
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={handleVerifyPackage}
              disabled={isVerifyingPkg || !verifyPkgFilename}
              className="text-xs"
            >
              {isVerifyingPkg ? 'Verifying...' : 'Verify Hash Integrity'}
            </Button>
          </div>

          {pkgVerifyResult && (
            <div className={`p-3 rounded text-xs space-y-1.5 font-mono ${
              pkgVerifyResult.is_valid
                ? 'bg-zinc-900 border border-zinc-700 text-zinc-200'
                : 'bg-zinc-900 border border-zinc-700 text-white'
            }`}>
              <div className="flex items-center justify-between font-bold">
                <span className="flex items-center gap-1.5">
                  {pkgVerifyResult.is_valid ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                  )}
                  {pkgVerifyResult.status}
                </span>
                <span className="text-[10px] text-zinc-400">
                  {pkgVerifyResult.verified_files_count} files checked
                </span>
              </div>
              <div className="text-[10px] text-zinc-400 break-all">
                Manifest Sig: {pkgVerifyResult.recorded_manifest_hash.substring(0, 24)}...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-400" />
          <span className="text-zinc-400 text-[11px] font-semibold uppercase">Type:</span>

          <button
            onClick={() => setTypeFilter('ALL')}
            className={`px-2 py-1 rounded text-xs transition-colors ${typeFilter === 'ALL' ? 'bg-white text-black font-semibold' : 'bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-800'}`}
          >
            All ({evidence.length})
          </button>

          <button
            onClick={() => setTypeFilter('CROP_PLATE')}
            className={`px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors ${typeFilter === 'CROP_PLATE' ? 'bg-emerald-500 text-black font-bold' : 'bg-zinc-900 text-emerald-300 hover:bg-zinc-800 border border-zinc-800'}`}
          >
            <Car className="w-3 h-3" /> Plate Crops ({evidence.filter(e => e.file_type === 'CROP_PLATE').length})
          </button>

          <button
            onClick={() => setTypeFilter('CROP_FACE')}
            className={`px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors ${typeFilter === 'CROP_FACE' ? 'bg-cyan-500 text-black font-bold' : 'bg-zinc-900 text-cyan-300 hover:bg-zinc-800 border border-zinc-800'}`}
          >
            <UserCheck className="w-3 h-3" /> Face Crops ({evidence.filter(e => e.file_type === 'CROP_FACE').length})
          </button>

          <button
            onClick={() => setTypeFilter('SNAPSHOT')}
            className={`px-2 py-1 rounded text-xs transition-colors ${typeFilter === 'SNAPSHOT' ? 'bg-white text-black font-semibold' : 'bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-800'}`}
          >
            Snapshots ({evidence.filter(e => e.file_type === 'SNAPSHOT').length})
          </button>

          <button
            onClick={() => setTypeFilter('CLIP')}
            className={`px-2 py-1 rounded text-xs transition-colors ${typeFilter === 'CLIP' ? 'bg-white text-black font-semibold' : 'bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-800'}`}
          >
            Clips ({evidence.filter(e => e.file_type === 'CLIP').length})
          </button>
        </div>

        <div className="relative flex-1 max-w-xs min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search evidence ID, plate, hash..."
            className="w-full bg-black border border-zinc-800 rounded pl-8 pr-3 py-1 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white font-mono"
          />
        </div>
      </div>

      {/* Evidence Table */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
        <div className="p-3 border-b border-zinc-800 flex items-center justify-between text-xs bg-zinc-900/50">
          <div className="font-semibold text-white uppercase tracking-wider">
            Evidence Catalog ({filteredEvidence.length} Displayed)
          </div>
          <span className="text-zinc-400 text-[11px] font-mono">
            Cryptographic Tamper-Evident SHA-256 Ledger
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase tracking-wider">
              <tr>
                <th className="p-3">PREVIEW</th>
                <th className="p-3">TYPE</th>
                <th className="p-3">INCIDENT REF</th>
                <th className="p-3">RECORDED AT</th>
                <th className="p-3">CAMERA</th>
                <th className="p-3">SHA-256 INTEGRITY</th>
                <th className="p-3 text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800 text-zinc-300">
              {filteredEvidence.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-12 text-center text-zinc-500 text-xs">
                    No evidence records matching current filter in repository.
                  </td>
                </tr>
              ) : (
                filteredEvidence.map((item) => {
                  const isClip = item.file_type === 'CLIP';
                  const ver = verificationStatus[item.id];
                  return (
                    <tr key={item.id} className="hover:bg-zinc-900/50 transition-colors">
                      <td className="p-3">
                        <div
                          onClick={() => setPreviewItem(item)}
                          className="w-14 h-10 bg-black rounded border border-zinc-700 overflow-hidden cursor-pointer flex items-center justify-center hover:opacity-80 transition-opacity shadow-sm"
                        >
                          {isClip ? (
                            <Film className="w-4 h-4 text-zinc-400" />
                          ) : (
                            <img
                              src={getMediaUrl(item.file_path)}
                              alt="thumb"
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                          )}
                        </div>
                      </td>
                      <td className="p-3">
                        {getTypeBadge(item.file_type)}
                      </td>
                      <td className="p-3 font-mono text-zinc-300">
                        {item.incident_id ? `INC-${item.incident_id}` : 'Direct Custody'}
                      </td>
                      <td className="p-3 font-mono text-zinc-400 text-[11px]">
                        {new Date(item.created_at).toLocaleString()}
                      </td>
                      <td className="p-3 font-mono text-zinc-400">
                        Cam #{item.camera_id}
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span
                            className="font-mono text-[11px] text-zinc-300 truncate max-w-[140px] cursor-pointer hover:text-white"
                            title={item.sha256_hash}
                            onClick={() => copyToClipboard(item.sha256_hash)}
                          >
                            {item.sha256_hash.substring(0, 16)}...
                          </span>
                          <button
                            onClick={() => copyToClipboard(item.sha256_hash)}
                            title="Copy SHA-256 Hash"
                            className="text-zinc-500 hover:text-white"
                          >
                            {copiedHash === item.sha256_hash ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>

                          {ver ? (
                            <span className={`text-[11px] flex items-center gap-1 font-mono font-bold ${ver.is_valid ? 'text-emerald-400' : 'text-red-400'}`}>
                              {ver.is_valid ? (
                                <>
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  VERIFIED
                                </>
                              ) : (
                                <>
                                  <AlertTriangle className="w-3.5 h-3.5" />
                                  TAMPERED
                                </>
                              )}
                            </span>
                          ) : (
                            <button
                              onClick={() => handleVerify(item.id)}
                              disabled={verifyingId === item.id}
                              className="text-xs text-zinc-400 hover:text-white underline ml-1 font-mono"
                            >
                              {verifyingId === item.id ? 'Auditing...' : 'Verify'}
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            icon={<Eye className="w-3 h-3" />}
                            onClick={() => setPreviewItem(item)}
                          >
                            View
                          </Button>
                          <a
                            href={getMediaUrl(item.file_path)}
                            download
                            className="p-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white"
                          >
                            <Download className="w-3 h-3" />
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Media Inspection Modal */}
      {previewItem && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-md max-w-2xl w-full p-4 space-y-3 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <span className="font-semibold text-white text-xs uppercase tracking-wider font-mono flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-emerald-400" />
                Evidence #{previewItem.id} — {previewItem.file_type}
              </span>
              <button
                onClick={() => setPreviewItem(null)}
                className="text-zinc-400 hover:text-white text-xs px-2 py-1"
              >
                ✕ Close
              </button>
            </div>

            <div className="bg-black border border-zinc-800 rounded overflow-hidden aspect-video flex items-center justify-center">
              {previewItem.file_type === 'CLIP' ? (
                <video
                  src={getMediaUrl(previewItem.file_path)}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              ) : (
                <img
                  src={getMediaUrl(previewItem.file_path)}
                  alt="Full Evidence"
                  className="w-full h-full object-contain"
                />
              )}
            </div>

            <div className="p-3 bg-black border border-zinc-800 rounded text-xs font-mono space-y-2 text-zinc-300">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-zinc-400 uppercase">Cryptographic SHA-256 Proof</span>
                <button
                  onClick={() => copyToClipboard(previewItem.sha256_hash)}
                  className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1"
                >
                  <Copy className="w-3 h-3" /> Copy Hash
                </button>
              </div>
              <div className="text-zinc-200 break-all text-[11px] bg-zinc-950 p-1.5 rounded border border-zinc-900">
                {previewItem.sha256_hash}
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] text-zinc-400 pt-1">
                <div>Recorded: <span className="text-white">{new Date(previewItem.created_at).toLocaleString()}</span></div>
                <div>Size: <span className="text-white">{(previewItem.file_size_bytes / 1024).toFixed(1)} KB</span></div>
                <div>Camera: <span className="text-white">#{previewItem.camera_id}</span></div>
                <div>Incident Ref: <span className="text-white">{previewItem.incident_id ? `INC-${previewItem.incident_id}` : 'None'}</span></div>
              </div>

              {previewItem.metadata_json && previewItem.metadata_json !== '{}' && (
                <div className="pt-2 border-t border-zinc-900 text-[10px] text-zinc-400">
                  <span className="text-zinc-500 block uppercase">Metadata</span>
                  <pre className="bg-zinc-950 p-1.5 rounded border border-zinc-900 overflow-x-auto text-zinc-300 font-mono mt-0.5">
                    {previewItem.metadata_json}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
              <a
                href={getMediaUrl(previewItem.file_path)}
                download
                className="px-3 py-1.5 bg-white text-black font-semibold text-xs rounded hover:bg-zinc-200 flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" /> Download Evidence File
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
