import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { clubsApi } from '../../../../services/api';
import type {
  Club,
  ClubImportJob,
  ClubImportJobListItem,
  ClubImportType,
  ClubResource,
  ClubResourceEngagement,
  ClubResourceEngagementVisibility,
  ClubResourceMyStatus,
} from '../../../../types/club';
import styles from './css/ClubResourceSection.module.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface ClubResourcesSectionProps {
  club: Club;
  isMember: boolean;
  canManageResources: boolean;
}

type ResourceStatusMap = Record<number, ClubResourceMyStatus>;
type UnknownRecord = Record<string, unknown>;

const ACCEPTED_RESOURCE_TYPES = '.pdf,.docx,.pptx,.xlsx,.csv,.png,.jpg,.jpeg,.webp';
const ACCEPTED_EXTENSIONS = ACCEPTED_RESOURCE_TYPES.split(',').map((e) => e.trim());

function extractDrfMessage(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null;
  const obj = data as Record<string, unknown>;
  for (const value of Object.values(obj)) {
    if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'string') return value[0];
    if (typeof value === 'string' && value.length > 0) return value;
  }
  return null;
}

function classifyUploadError(err: unknown): string {
  if (err instanceof TypeError) return 'File upload failed: your internet connection was interrupted.';
  const apiErr = err as { status?: number; data?: unknown };
  const status = apiErr.status;
  const drfMessage = extractDrfMessage(apiErr.data);
  const rawMessage = drfMessage ?? (err instanceof Error ? err.message : '');
  const lower = rawMessage.toLowerCase();
  if (status === 413 || lower.includes('too large') || lower.includes('exceeds')) return 'File upload failed: the file is too large.';
  if (status === 415 || lower.includes('unsupported file type') || lower.includes('extension')) return `File upload failed: unsupported type. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}.`;
  if (status === 400) return rawMessage ? `File upload failed: ${rawMessage}` : 'File upload failed: invalid request.';
  if (status === 403) return 'File upload failed: you do not have permission.';
  if (status === 401) return 'File upload failed: you must be logged in.';
  if (status !== undefined && status >= 500) return 'File upload failed: server error. Try again later.';
  return rawMessage ? `File upload failed: ${rawMessage}` : 'File upload failed: something went wrong.';
}

const HEARTBEAT_INTERVAL_MS = 15000;

const IMPORT_TYPE_OPTIONS: Array<{ value: ClubImportType; label: string; description: string }> = [
  { value: 'player_profile_update', label: 'Player profile update', description: 'Update club-local ClubPlayer fields such as display name, number, position, or height.' },
  { value: 'player_season_stats', label: 'Player season stats', description: 'Create or update season-level player enrichment rows for linked canonical players.' },
  { value: 'squad_metrics', label: 'Squad metrics', description: 'Create or update season-level club enrichment rows such as wins, goals, xG, and PPDA.' },
  { value: 'other', label: 'Other / raw preview', description: 'Preview the CSV/XLSX contents without requiring a structured import schema.' },
];

const getFileKindLabel = (r: ClubResource): string => {
  const map: Record<string, string> = { pdf: 'PDF', docx: 'DOCX', pptx: 'PPTX', xlsx: 'XLSX', csv: 'CSV', image: 'Image' };
  return map[r.file_kind] ?? 'File';
};
const getVisibilityLabel = (v: ClubResourceEngagementVisibility) => v === 'club_visible' ? 'Club visible' : 'Staff only';
const getImportTypeLabel = (v: ClubImportType) => IMPORT_TYPE_OPTIONS.find((o) => o.value === v)?.label ?? v;
const getImportStatusLabel = (v: string): string => {
  const map: Record<string, string> = { uploaded: 'Uploaded', validating: 'Validating', preview_ready: 'Preview ready', confirmed: 'Confirmed', processing: 'Processing', completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled' };
  return map[v] ?? v;
};
const formatFileSize = (bytes: number) => bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
const formatDateTime = (v: string | null): string | null => v ? new Date(v).toLocaleString('en-IE', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : null;
const getMyStatusLabel = (s: ClubResourceMyStatus | undefined): string => {
  if (!s?.my_view_summary) return 'Not opened';
  if (s.my_view_summary.completed) return 'Completed';
  if (s.my_view_summary.opened) return 'Opened';
  return 'Not opened';
};

const asRecord = (v: unknown): UnknownRecord => (v && typeof v === 'object' && !Array.isArray(v)) ? (v as UnknownRecord) : {};
const asArray = <T,>(v: unknown): T[] => Array.isArray(v) ? (v as T[]) : [];
const formatUnknownValue = (v: unknown): string => {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'string') return v;
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  if (Array.isArray(v)) return v.map(formatUnknownValue).join(', ');
  try { return JSON.stringify(v); } catch { return String(v); }
};
const getPreviewCounts = (j: ClubImportJob | null) => asRecord(asRecord(j?.preview_payload).counts);
const getReportCounts = (j: ClubImportJob | null) => asRecord(asRecord(j?.report_payload).counts);
const getPreviewRows = (j: ClubImportJob | null) => asArray<UnknownRecord>(asRecord(j?.preview_payload).rows);
const getPreviewHeaders = (j: ClubImportJob | null) => asArray<string>(asRecord(j?.preview_payload).headers);
const getRawPreviewRows = (j: ClubImportJob | null) => asArray<UnknownRecord>(asRecord(j?.preview_payload).rows);
const getReportErrors = (j: ClubImportJob | null) => asArray<UnknownRecord>(asRecord(j?.report_payload).errors);
const getErrorSummaryMessage = (j: ClubImportJob | null): string | null => {
  const s = asRecord(j?.error_summary); const m = s.message;
  return typeof m === 'string' && m.trim() ? m : null;
};

const FileKindIcon = ({ kind }: { kind: string }) => {
  const icons: Record<string, string> = { pdf: '📄', docx: '📝', pptx: '📊', xlsx: '📈', csv: '🗂', image: '🖼' };
  return <span style={{ fontSize: '1.1rem' }}>{icons[kind] ?? '📁'}</span>;
};

export const ClubResourcesSection = ({ club, isMember, canManageResources }: ClubResourcesSectionProps) => {
  const uploadTitleInputId = `club-resource-upload-title-${club.id}`;
  const uploadDescriptionInputId = `club-resource-upload-description-${club.id}`;
  const uploadVisibilitySelectId = `club-resource-upload-visibility-${club.id}`;
  const uploadFileInputId = `club-resource-upload-file-${club.id}`;
  const importResourceSelectId = `club-import-resource-${club.id}`;
  const importTypeSelectId = `club-import-type-${club.id}`;

  const [resources, setResources] = useState<ClubResource[]>([]);
  const [resourceStatuses, setResourceStatuses] = useState<ResourceStatusMap>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadVisibility, setUploadVisibility] = useState<ClubResourceEngagementVisibility>('staff_only');
  const [uploading, setUploading] = useState(false);
  const [resourceActionMessage, setResourceActionMessage] = useState<string | null>(null);
  const [resourceUploadError, setResourceUploadError] = useState<string | null>(null);
  const [selectedEngagement, setSelectedEngagement] = useState<ClubResourceEngagement | null>(null);
  const [selectedEngagementResourceId, setSelectedEngagementResourceId] = useState<number | null>(null);
  const [engagementLoading, setEngagementLoading] = useState(false);
  const [viewerResource, setViewerResource] = useState<ClubResource | null>(null);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);
  const viewerFile = useMemo(() => viewerUrl ? (import.meta.env.DEV ? { url: viewerUrl, withCredentials: true } : viewerUrl) : null, [viewerUrl]);
  const [viewerLoading, setViewerLoading] = useState(false);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [viewerPage, setViewerPage] = useState(1);
  const [viewerPageCount, setViewerPageCount] = useState(0);
  const [canAccessImports, setCanAccessImports] = useState(false);
  const [importJobs, setImportJobs] = useState<ClubImportJobListItem[]>([]);
  const [importLoading, setImportLoading] = useState(false);
  const [selectedImportJob, setSelectedImportJob] = useState<ClubImportJob | null>(null);
  const [selectedResourceId, setSelectedResourceId] = useState<number | null>(null);
  const [selectedImportType, setSelectedImportType] = useState<ClubImportType>('player_profile_update');
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [creatingPreview, setCreatingPreview] = useState(false);
  const [loadingImportDetail, setLoadingImportDetail] = useState(false);
  const [committingImport, setCommittingImport] = useState(false);
  const [showUploadForm, setShowUploadForm] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const currentPageRef = useRef(1);
  const activeViewerResourceRef = useRef<ClubResource | null>(null);
  const lastHeartbeatAtRef = useRef<number | null>(null);

  const importableResources = useMemo(
    () => resources.filter((r) => !r.is_archived && (r.file_kind === 'csv' || r.file_kind === 'xlsx')),
    [resources]
  );

  useEffect(() => {
    if (!selectedResourceId && importableResources.length > 0) setSelectedResourceId(importableResources[0].id);
    if (selectedResourceId && !importableResources.some((r) => r.id === selectedResourceId)) setSelectedResourceId(importableResources[0]?.id ?? null);
  }, [importableResources, selectedResourceId]);

  const loadStatuses = useCallback(async (list: ClubResource[]) => {
    if (!isMember || list.length === 0) { setResourceStatuses({}); return; }
    const entries = await Promise.all(list.map(async (r) => { try { const s = await clubsApi.getMyResourceStatus(club.id, r.id); return [r.id, s] as const; } catch { return [r.id, null] as const; } }));
    const next: ResourceStatusMap = {};
    entries.forEach(([id, s]) => { if (s) next[id] = s; });
    setResourceStatuses(next);
  }, [club.id, isMember]);

  const loadResources = useCallback(async () => {
    if (!isMember) { setResources([]); setResourceStatuses({}); return; }
    try {
      setLoading(true); setError(null);
      const list = await clubsApi.listResources(club.id);
      setResources(list); await loadStatuses(list);
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load club resources.'); }
    finally { setLoading(false); }
  }, [club.id, isMember, loadStatuses]);

  const loadImportJobs = useCallback(async () => {
    if (!isMember) { setCanAccessImports(false); setImportJobs([]); setSelectedImportJob(null); return; }
    try {
      setImportLoading(true);
      const jobs = await clubsApi.listImportJobs(club.id);
      setImportJobs(jobs); setCanAccessImports(true);
    } catch { setCanAccessImports(false); setImportJobs([]); setSelectedImportJob(null); }
    finally { setImportLoading(false); }
  }, [club.id, isMember]);

  useEffect(() => { void loadResources(); void loadImportJobs(); }, [loadResources, loadImportJobs]);

  const sendHeartbeat = useCallback(async (resourceId: number, activeDelta: number, page: number | null) => {
    await clubsApi.sendResourceHeartbeat(club.id, resourceId, { active_seconds_delta: activeDelta, page_reached: page });
  }, [club.id]);

  const flushPdfHeartbeat = useCallback(() => {
    const active = activeViewerResourceRef.current;
    const last = lastHeartbeatAtRef.current;
    if (!active || !last) return;
    const elapsed = Math.max(0, Math.floor((Date.now() - last) / 1000));
    if (elapsed <= 0) return;
    lastHeartbeatAtRef.current = null;
    void sendHeartbeat(active.id, elapsed, currentPageRef.current);
  }, [sendHeartbeat]);

  useEffect(() => {
    if (!viewerResource || !viewerUrl) return;
    activeViewerResourceRef.current = viewerResource;
    lastHeartbeatAtRef.current = Date.now();
    void clubsApi.getMyResourceStatus(club.id, viewerResource.id)
      .then((s) => setResourceStatuses((c) => ({ ...c, [viewerResource.id]: s }))).catch(() => undefined);
    const id = window.setInterval(() => {
      const last = lastHeartbeatAtRef.current;
      if (!last) return;
      const elapsed = Math.max(0, Math.floor((Date.now() - last) / 1000));
      if (elapsed <= 0) return;
      lastHeartbeatAtRef.current = Date.now();
      void sendHeartbeat(viewerResource.id, elapsed, currentPageRef.current)
        .then(() => clubsApi.getMyResourceStatus(club.id, viewerResource.id))
        .then((s) => setResourceStatuses((c) => ({ ...c, [viewerResource.id]: s }))).catch(() => undefined);
    }, HEARTBEAT_INTERVAL_MS);
    return () => { window.clearInterval(id); flushPdfHeartbeat(); activeViewerResourceRef.current = null; };
  }, [club.id, flushPdfHeartbeat, sendHeartbeat, viewerPage, viewerResource, viewerUrl]);

  useEffect(() => { currentPageRef.current = viewerPage; }, [viewerPage]);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadTitle.trim()) { setResourceActionMessage('Resource title is required.'); return; }
    if (!uploadFile) { setResourceActionMessage('Choose a supported file before uploading.'); return; }
    try {
      setUploading(true); setResourceActionMessage(null); setResourceUploadError(null);
      await clubsApi.uploadResource(club.id, { title: uploadTitle.trim(), description: uploadDescription.trim(), file: uploadFile, engagement_visibility: uploadVisibility });
      setUploadTitle(''); setUploadDescription(''); setUploadFile(null); setUploadVisibility('staff_only');
      if (fileInputRef.current) fileInputRef.current.value = '';
      setResourceActionMessage('Resource uploaded successfully.'); setShowUploadForm(false);
      await loadResources();
    } catch (err) { setResourceUploadError(classifyUploadError(err)); }
    finally { setUploading(false); }
  };

  const handleOpenResource = async (resource: ClubResource) => {
    try {
      setResourceActionMessage(null); setViewerError(null); setViewerLoading(true);
      const access = await clubsApi.getResourceAccess(club.id, resource.id);
      if (resource.can_inline_view) {
        setViewerResource(resource); setViewerUrl(access.access_url); setViewerPage(1); setViewerPageCount(0);
      } else {
        await clubsApi.sendResourceHeartbeat(club.id, resource.id, { active_seconds_delta: 0, page_reached: null });
        const s = await clubsApi.getMyResourceStatus(club.id, resource.id);
        setResourceStatuses((c) => ({ ...c, [resource.id]: s }));
        window.open(access.access_url, '_blank', 'noopener,noreferrer');
      }
    } catch (err) {
      const m = err instanceof Error ? err.message : 'Failed to open this resource.';
      setViewerError(m); setResourceActionMessage(m);
    } finally { setViewerLoading(false); }
  };

  const handleDownloadResource = async (resource: ClubResource) => {
    try {
      setResourceActionMessage(null); setViewerError(null); setViewerLoading(true);
      const access = await clubsApi.getResourceAccess(club.id, resource.id);
      const link = document.createElement('a');
      link.href = access.access_url; link.download = resource.original_filename ?? 'resource';
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      document.body.appendChild(link); link.click(); document.body.removeChild(link);
      const s = await clubsApi.getMyResourceStatus(club.id, resource.id);
      setResourceStatuses((c) => ({ ...c, [resource.id]: s }));
    } catch (err) {
      const m = err instanceof Error ? err.message : 'Failed to download this resource.';
      setViewerError(m); setResourceActionMessage(m);
    } finally { setViewerLoading(false); }
  };

  const handleCloseViewer = async () => {
    flushPdfHeartbeat();
    if (viewerResource) {
      try { const s = await clubsApi.getMyResourceStatus(club.id, viewerResource.id); setResourceStatuses((c) => ({ ...c, [viewerResource.id]: s })); } catch { return; }
    }
    setViewerResource(null); setViewerUrl(null); setViewerPage(1); setViewerPageCount(0);
    setViewerError(null); activeViewerResourceRef.current = null; lastHeartbeatAtRef.current = null;
  };

  const handleLoadEngagement = async (resource: ClubResource) => {
    try {
      setEngagementLoading(true); setResourceActionMessage(null);
      const eng = await clubsApi.getResourceEngagement(club.id, resource.id);
      setSelectedEngagement(eng); setSelectedEngagementResourceId(resource.id);
    } catch (err) {
      setSelectedEngagement(null); setSelectedEngagementResourceId(resource.id);
      setResourceActionMessage(err instanceof Error ? err.message : 'Detailed engagement is only available to authorised club staff.');
    } finally { setEngagementLoading(false); }
  };

  const handleCreateImportPreview = async () => {
    if (!selectedResourceId) { setImportMessage('Select a CSV or XLSX resource first.'); return; }
    try {
      setCreatingPreview(true); setImportMessage(null);
      const job = await clubsApi.createImportJob(club.id, { source_resource: selectedResourceId, import_type: selectedImportType });
      setSelectedImportJob(job); await loadImportJobs();
      setImportMessage(job.status === 'preview_ready' ? 'Preview created successfully.' : job.status === 'failed' ? 'Import preview failed. Review the report below.' : `Import job created with status: ${getImportStatusLabel(job.status)}.`);
    } catch (err) { setImportMessage(err instanceof Error ? err.message : 'Failed to create import preview.'); }
    finally { setCreatingPreview(false); }
  };

  const handleSelectImportJob = async (jobId: number) => {
    try { setLoadingImportDetail(true); setImportMessage(null); const d = await clubsApi.getImportJob(club.id, jobId); setSelectedImportJob(d); }
    catch (err) { setImportMessage(err instanceof Error ? err.message : 'Failed to load import job details.'); }
    finally { setLoadingImportDetail(false); }
  };

  const handleCommitImport = async () => {
    if (!selectedImportJob || !window.confirm('This will commit the matched preview rows to the database. Continue?')) return;
    try {
      setCommittingImport(true); setImportMessage(null);
      const committed = await clubsApi.commitImportJob(club.id, selectedImportJob.id, { confirm: true });
      setSelectedImportJob(committed); await loadImportJobs();
      setImportMessage(committed.status === 'completed' ? 'Import committed successfully.' : `Commit finished with status: ${getImportStatusLabel(committed.status)}.`);
    } catch (err) { setImportMessage(err instanceof Error ? err.message : 'Failed to commit import job.'); }
    finally { setCommittingImport(false); }
  };

  const previewCounts = getPreviewCounts(selectedImportJob);
  const previewRows = getPreviewRows(selectedImportJob);
  const previewHeaders = getPreviewHeaders(selectedImportJob).slice(0, 5);
  const allRawPreviewRows = getRawPreviewRows(selectedImportJob);
  const rawPreviewRows = allRawPreviewRows.slice(0, 5);
  const rawPreviewRowCount = allRawPreviewRows.length;
  const isRawPreview = Boolean(asRecord(selectedImportJob?.preview_payload).raw_preview) || selectedImportJob?.import_type === 'other';
  const reportCounts = getReportCounts(selectedImportJob);
  const reportErrors = getReportErrors(selectedImportJob);
  const previewCanCommit = Boolean(asRecord(selectedImportJob?.preview_payload).can_commit);
  const selectedImportOption = IMPORT_TYPE_OPTIONS.find((o) => o.value === selectedImportType);

  if (!isMember) {
    return (
      <div className={styles.clubResourceSection}>
        <div className={styles.clubResourceSectionHead}>
          <h2 className={styles.clubResourceSectionTitle}>Club Resources</h2>
          <p className={styles.clubResourceSectionSub}>Resources become available once you are an active member of the club.</p>
        </div>
      </div>
    );
  }

  const visibleResources = resources.filter(
    (r) => r.engagement_visibility === 'club_visible' || (r.engagement_visibility === 'staff_only' && canManageResources)
  );

  return (
    <section className={styles.clubResourceSection}>

      <div className={styles.clubResourceSectionHead}>
        <div>
          <h2 className={styles.clubResourceSectionTitle}>Club Resources</h2>
          <p className={styles.clubResourceSectionSub}>
            {canManageResources
              ? 'Upload learning material, analysis packs, spreadsheets, and other club files.'
              : 'Access learning material, analysis packs, and other club files.'
            }
          </p>
        </div>
        {canManageResources && (
          <button
            className={styles.clubResourceUploadTrigger}
            type="button"
            onClick={() => setShowUploadForm((v) => !v)}
          >
            {showUploadForm ? '✕ Cancel upload' : '+ Upload file'}
          </button>
        )}
      </div>

      {error && <div className={styles.clubResourceError}>{error}</div>}
      {resourceUploadError && <div className={styles.clubResourceError}>{resourceUploadError}</div>}
      {resourceActionMessage && <div className={styles.clubResourceNotice}>{resourceActionMessage}</div>}

      {canManageResources && showUploadForm && (
        <div className={styles.clubResourceUploadPanel}>
          <h3 className={styles.clubResourcePanelTitle}>Upload resource</h3>
          <p className={styles.clubResourcePanelSub}>
            Coaches and authorised staff can upload PDFs, Word, PowerPoint, Excel, CSV, and images.
          </p>
          <form className={styles.clubResourceForm} onSubmit={handleUploadSubmit}>
            <div className={styles.clubResourceFormGrid}>
              <div className={styles.clubResourceFormField}>
                <label className={styles.clubResourceLabel} htmlFor={uploadTitleInputId}>TITLE</label>
                <input id={uploadTitleInputId} className={styles.clubResourceInput} type="text" value={uploadTitle} onChange={(e) => setUploadTitle(e.target.value)} placeholder="e.g. Matchday analysis pack" />
              </div>
              <div className={styles.clubResourceFormField}>
                <label className={styles.clubResourceLabel} htmlFor={uploadVisibilitySelectId}>VISIBILITY</label>
                <select id={uploadVisibilitySelectId} className={styles.clubResourceSelect} value={uploadVisibility} onChange={(e) => setUploadVisibility(e.target.value as ClubResourceEngagementVisibility)}>
                  <option value="staff_only">Staff only</option>
                  <option value="club_visible">Club visible</option>
                </select>
              </div>
            </div>
            <div className={styles.clubResourceFormField}>
              <label className={styles.clubResourceLabel} htmlFor={uploadDescriptionInputId}>DESCRIPTION</label>
              <textarea id={uploadDescriptionInputId} className={styles.clubResourceTextarea} rows={3} value={uploadDescription} onChange={(e) => setUploadDescription(e.target.value)} placeholder="Optional context for players and staff." />
            </div>
            <div className={styles.clubResourceFormField}>
              <label className={styles.clubResourceLabel} htmlFor={uploadFileInputId}>FILE</label>
              <input ref={fileInputRef} id={uploadFileInputId} className={styles.clubResourceFileInput} type="file" accept={ACCEPTED_RESOURCE_TYPES} onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)} />
              <p className={styles.clubResourceHelperText}>Supported: PDF, DOCX, PPTX, XLSX, CSV, PNG, JPG, JPEG, WEBP.</p>
            </div>
            <div className={styles.clubResourceActionRow}>
              <button className={styles.clubResourcePrimaryBtn} type="submit" disabled={uploading}>
                {uploading ? 'Uploading…' : 'Upload resource'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className={styles.clubResourceLibrary}>
        {loading ? (
          <div className={styles.clubResourceEmpty}>Loading club resources…</div>
        ) : visibleResources.length === 0 ? (
          <div className={styles.clubResourceEmpty}>
            {resources.length === 0 ? 'No resources uploaded yet.' : 'No resources available for your access level.'}
          </div>
        ) : (
          <div className={styles.clubResourceGrid}>
            {visibleResources.map((resource) => {
              const myStatus = resourceStatuses[resource.id];
              const statusLabel = getMyStatusLabel(myStatus);
              const isEngagementOpen = selectedEngagementResourceId === resource.id;

              return (
                <div key={resource.id} className={styles.clubResourceCard}>
                  <div className={styles.clubResourceCardTop}>
                    <div className={styles.clubResourceCardIcon}>
                      <FileKindIcon kind={resource.file_kind} />
                    </div>
                    <div className={styles.clubResourceCardInfo}>
                      <div className={styles.clubResourceCardName}>{resource.title}</div>
                      <div className={styles.clubResourceCardFile}>{resource.original_filename}</div>
                    </div>
                    <span className={styles.clubResourceKindPill}>{getFileKindLabel(resource)}</span>
                  </div>

                  {resource.description && (
                    <p className={styles.clubResourceCardDesc}>{resource.description}</p>
                  )}

                  <div className={styles.clubResourceMeta}>
                    <div className={styles.clubResourceMetaItem}>
                      <span className={styles.clubResourceMetaLabel}>Size</span>
                      <span className={styles.clubResourceMetaValue}>{formatFileSize(resource.file_size_bytes)}</span>
                    </div>
                    <div className={styles.clubResourceMetaItem}>
                      <span className={styles.clubResourceMetaLabel}>Visibility</span>
                      <span className={styles.clubResourceMetaValue}>{getVisibilityLabel(resource.engagement_visibility)}</span>
                    </div>
                    <div className={styles.clubResourceMetaItem}>
                      <span className={styles.clubResourceMetaLabel}>Your status</span>
                      <span className={`${styles.clubResourceMetaValue} ${statusLabel === 'Completed' ? styles.clubResourceStatusComplete : statusLabel === 'Opened' ? styles.clubResourceStatusOpened : ''}`}>
                        {statusLabel}
                      </span>
                    </div>
                    <div className={styles.clubResourceMetaItem}>
                      <span className={styles.clubResourceMetaLabel}>Uploaded</span>
                      <span className={styles.clubResourceMetaValue}>{formatDateTime(resource.created_at) ?? '—'}</span>
                    </div>
                  </div>

                  <div className={styles.clubResourceCardActions}>
                    <button className={styles.clubResourcePrimaryBtn} type="button" disabled={viewerLoading} onClick={() => handleOpenResource(resource)}>
                      {resource.can_inline_view ? 'Open inline' : 'Open'}
                    </button>
                    <button className={styles.clubResourceGhostBtn} type="button" disabled={viewerLoading} onClick={() => handleDownloadResource(resource)}>
                      Download
                    </button>
                    {canManageResources && (
                      <button className={styles.clubResourceGhostBtn} type="button" disabled={engagementLoading} onClick={() => handleLoadEngagement(resource)}>
                        {isEngagementOpen && engagementLoading ? 'Loading…' : 'Engagement'}
                      </button>
                    )}
                  </div>

                  {isEngagementOpen && selectedEngagement && (
                    <div className={styles.clubResourceEngagementPanel}>
                      <div className={styles.clubResourceEngagementSummary}>
                        <span>Viewers: {selectedEngagement.total_viewers}</span>
                        <span>Opened: {selectedEngagement.opened_count}</span>
                        <span>Completed: {selectedEngagement.completed_count}</span>
                      </div>
                      {selectedEngagement.resource_views.length === 0 ? (
                        <div className={styles.clubResourceEmpty}>No engagement recorded yet.</div>
                      ) : (
                        <div className={styles.clubResourceTableWrap}>
                          <table className={styles.clubResourceTable}>
                            <thead>
                              <tr>
                                <th>User</th><th>Opened</th><th>Completed</th><th>Active sec</th><th>Highest page</th><th>Last opened</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedEngagement.resource_views.map((v) => (
                                <tr key={v.id}>
                                  <td>{v.user_email}</td>
                                  <td>{v.opened ? 'Yes' : 'No'}</td>
                                  <td>{v.completed ? 'Yes' : 'No'}</td>
                                  <td>{v.total_active_seconds}</td>
                                  <td>{v.highest_page_reached}</td>
                                  <td>{formatDateTime(v.last_opened_at) ?? '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {canAccessImports && (
        <div className={styles.clubResourceImportSection}>
          <div className={styles.clubResourceSectionHead}>
            <div>
              <h3 className={styles.clubResourcePanelTitle}>Structured imports</h3>
              <p className={styles.clubResourcePanelSub}>Create a preview from a CSV/XLSX resource, review matched rows, then confirm the commit.</p>
            </div>
          </div>

          {importMessage && <div className={styles.clubResourceNotice}>{importMessage}</div>}

          <div className={styles.clubResourceImportBuilder}>
            <div className={styles.clubResourceFormGrid}>
              <div className={styles.clubResourceFormField}>
                <label className={styles.clubResourceLabel} htmlFor={importResourceSelectId}>SOURCE RESOURCE</label>
                <select id={importResourceSelectId} className={styles.clubResourceSelect} value={selectedResourceId ?? ''} onChange={(e) => setSelectedResourceId(Number(e.target.value) || null)}>
                  {importableResources.length === 0
                    ? <option value="">No CSV/XLSX resources available</option>
                    : <><option value="">Select a resource</option>{importableResources.map((r) => <option key={r.id} value={r.id}>{r.title} · {r.original_filename}</option>)}</>
                  }
                </select>
              </div>
              <div className={styles.clubResourceFormField}>
                <label className={styles.clubResourceLabel} htmlFor={importTypeSelectId}>IMPORT TYPE</label>
                <select id={importTypeSelectId} className={styles.clubResourceSelect} value={selectedImportType} onChange={(e) => setSelectedImportType(e.target.value as ClubImportType)}>
                  {IMPORT_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                {selectedImportOption && <p className={styles.clubResourceHelperText}>{selectedImportOption.description}</p>}
              </div>
            </div>
            <button className={styles.clubResourcePrimaryBtn} type="button" disabled={creatingPreview || !selectedResourceId} onClick={() => void handleCreateImportPreview()}>
              {creatingPreview ? 'Creating preview…' : 'Create preview'}
            </button>
          </div>

          <div className={styles.clubResourceImportGrid}>
            <div className={styles.clubResourceImportHistory}>
              <div className={styles.clubResourceImportHistoryHead}>
                <span className={styles.clubResourcePanelTitle} style={{ fontSize: '0.85rem' }}>Import history</span>
                {importLoading && <span className={styles.clubResourceMutedText}>Loading…</span>}
              </div>
              {importJobs.length === 0 ? (
                <div className={styles.clubResourceEmpty}>No import jobs yet.</div>
              ) : (
                <div className={styles.clubResourceImportJobList}>
                  {importJobs.map((job) => {
                    const isSelected = selectedImportJob?.id === job.id;
                    return (
                      <button
                        key={job.id}
                        type="button"
                        className={`${styles.clubResourceImportJobCard} ${isSelected ? styles.clubResourceImportJobCardActive : ''}`}
                        onClick={() => void handleSelectImportJob(job.id)}
                      >
                        <div className={styles.clubResourceImportJobRow}>
                          <div className={styles.clubResourceImportJobTitle}>{getImportTypeLabel(job.import_type)}</div>
                          <span className={`${styles.clubResourceStatusPill} ${styles[`clubResourceStatus_${job.status}`] ?? ''}`}>
                            {getImportStatusLabel(job.status)}
                          </span>
                        </div>
                        <div className={styles.clubResourceImportJobMeta}>{job.source_resource_original_filename}</div>
                        <div className={styles.clubResourceImportJobMeta}>{job.valid_row_count} valid · {job.warning_count} warnings</div>
                        <div className={styles.clubResourceImportJobMeta}>Created {formatDateTime(job.created_at) ?? '—'}</div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className={styles.clubResourceImportDetail}>
              {loadingImportDetail ? (
                <div className={styles.clubResourceEmpty}>Loading import details…</div>
              ) : !selectedImportJob ? (
                <div className={styles.clubResourceEmpty}>Select an import job to review its preview or final report.</div>
              ) : (
                <div className={styles.clubResourceImportDetailCard}>
                  <div className={styles.clubResourceImportDetailHead}>
                    <div>
                      <div className={styles.clubResourceImportJobTitle}>{getImportTypeLabel(selectedImportJob.import_type)}</div>
                      <div className={styles.clubResourceImportJobMeta}>{selectedImportJob.source_resource_original_filename}</div>
                    </div>
                    <span className={`${styles.clubResourceStatusPill} ${styles[`clubResourceStatus_${selectedImportJob.status}`] ?? ''}`}>
                      {getImportStatusLabel(selectedImportJob.status)}
                    </span>
                  </div>

                  <div className={styles.clubResourceCountRow}>
                    {[
                      ['Valid', selectedImportJob.valid_row_count],
                      ['Warnings', selectedImportJob.warning_count],
                      ['Imported', formatUnknownValue(reportCounts.imported_rows ?? selectedImportJob.imported_row_count)],
                      ['Skipped', formatUnknownValue(reportCounts.skipped_rows ?? selectedImportJob.skipped_row_count)],
                      ['Failed', formatUnknownValue(reportCounts.failed_rows ?? selectedImportJob.failed_row_count)],
                    ].map(([label, val]) => (
                      <div key={label as string} className={styles.clubResourceCountCard}>
                        <span className={styles.clubResourceCountLabel}>{label}</span>
                        <span className={styles.clubResourceCountValue}>{val}</span>
                      </div>
                    ))}
                  </div>

                  {selectedImportJob.status === 'preview_ready' && previewCanCommit && (
                    <div className={styles.clubResourceCommitBar}>
                      <span className={styles.clubResourceCommitText}>Review the preview carefully before confirming the final commit.</span>
                      <button className={styles.clubResourceCommitBtn} type="button" disabled={committingImport} onClick={() => void handleCommitImport()}>
                        {committingImport ? 'Committing…' : 'Confirm and commit'}
                      </button>
                    </div>
                  )}
                  {selectedImportJob.status === 'preview_ready' && !previewCanCommit && (
                    <div className={styles.clubResourceNotice}>
                      {selectedImportJob.import_type === 'other' ? 'This preview cannot be committed; it is a raw file review only.' : 'This preview cannot be committed as a structured import.'}
                    </div>
                  )}

                  {isRawPreview && rawPreviewRows.length > 0 ? (
                    <div className={styles.clubResourcePreviewSection}>
                      <div className={styles.clubResourcePanelTitle} style={{ fontSize: '0.82rem' }}>Raw preview</div>
                      <div className={styles.clubResourceTableWrap}>
                        <table className={styles.clubResourceTable}>
                          <thead><tr><th>#</th><th>Status</th>{previewHeaders.map((h) => <th key={h}>{h}</th>)}</tr></thead>
                          <tbody>
                            {rawPreviewRows.map((row, i) => {
                              const num = typeof row.row_number === 'number' ? row.row_number : i + 1;
                              const st = typeof row.status === 'string' ? row.status : 'preview';
                              const raw = asRecord(row.raw_data);
                              return <tr key={num}><td>{formatUnknownValue(num)}</td><td>{st}</td>{previewHeaders.map((h) => <td key={h}>{formatUnknownValue(raw[h])}</td>)}</tr>;
                            })}
                          </tbody>
                        </table>
                      </div>
                      {rawPreviewRowCount > 5 && <div className={styles.clubResourceMutedText}>Showing the first 5 rows.</div>}
                    </div>
                  ) : previewRows.length > 0 ? (
                    <div className={styles.clubResourcePreviewSection}>
                      <div className={styles.clubResourcePanelTitle} style={{ fontSize: '0.82rem' }}>Preview rows</div>
                      {previewRows.slice(0, 10).map((row) => {
                        const rowNumber = row.row_number;
                        const rowStatus = typeof row.status === 'string' ? row.status : 'unknown';
                        const warnings = asArray<string>(row.warnings);
                        const errors = asArray<string>(row.errors);
                        const currentValues = asRecord(row.current_values);
                        const proposedChanges = asRecord(row.proposed_changes);
                        return (
                          <div key={typeof rowNumber === 'number' ? rowNumber : Math.random()} className={styles.clubResourcePreviewRowCard}>
                            <div className={styles.clubResourcePreviewRowHead}>
                              <div>
                                <div className={styles.clubResourceImportJobTitle}>Row {formatUnknownValue(rowNumber)}</div>
                                <div className={styles.clubResourceImportJobMeta}>{formatUnknownValue(row.target_label)} · {formatUnknownValue(row.match_method)}</div>
                              </div>
                              <span className={`${styles.clubResourceStatusPill} ${styles[`clubResourceStatus_${rowStatus}`] ?? ''}`}>{rowStatus}</span>
                            </div>
                            <div className={styles.clubResourcePreviewCols}>
                              <div>
                                <div className={styles.clubResourcePreviewColTitle}>Current values</div>
                                {Object.keys(currentValues).length === 0 ? (
                                  <div className={styles.clubResourceMutedText}>No existing values shown.</div>
                                ) : (
                                  <div className={styles.clubResourceKVList}>
                                    {Object.entries(currentValues).map(([k, v]) => (
                                      <div key={k} className={styles.clubResourceKVItem}>
                                        <span className={styles.clubResourceKVKey}>{k}</span>
                                        <span className={styles.clubResourceKVVal}>{formatUnknownValue(v)}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <div>
                                <div className={styles.clubResourcePreviewColTitle}>Proposed changes</div>
                                {Object.keys(proposedChanges).length === 0 ? (
                                  <div className={styles.clubResourceMutedText}>No changes proposed.</div>
                                ) : (
                                  <div className={styles.clubResourceKVList}>
                                    {Object.entries(proposedChanges).map(([k, v]) => {
                                      const change = asRecord(v);
                                      return (
                                        <div key={k} className={styles.clubResourceKVItem}>
                                          <span className={styles.clubResourceKVKey}>{k}</span>
                                          <div className={styles.clubResourceChangeValues}>
                                            <span>{formatUnknownValue(change.from)}</span>
                                            <span className={styles.clubResourceChangeArrow}>→</span>
                                            <span>{formatUnknownValue(change.to)}</span>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            </div>
                            {warnings.length > 0 && (
                              <div className={styles.clubResourceWarningPanel}>
                                <div className={styles.clubResourceWarningTitle}>Warnings</div>
                                <ul className={styles.clubResourceWarningList}>{warnings.map((w, i) => <li key={`${w}-${i}`}>{w}</li>)}</ul>
                              </div>
                            )}
                            {errors.length > 0 && (
                              <div className={styles.clubResourceErrorPanel}>
                                <div className={styles.clubResourceWarningTitle}>Errors</div>
                                <ul className={styles.clubResourceWarningList}>{errors.map((e, i) => <li key={`${e}-${i}`}>{e}</li>)}</ul>
                              </div>
                            )}
                          </div>
                        );
                      })}
                      {previewRows.length > 10 && <div className={styles.clubResourceMutedText}>Showing the first 10 rows.</div>}
                    </div>
                  ) : null}

                  {(selectedImportJob.status === 'completed' || selectedImportJob.status === 'failed') && (
                    <div className={styles.clubResourceReportSection}>
                      <div className={styles.clubResourcePanelTitle} style={{ fontSize: '0.82rem' }}>Final report</div>
                      <div className={styles.clubResourceCountRow}>
                        {[
                          ['Created', formatUnknownValue(reportCounts.created_rows ?? 0)],
                          ['Updated', formatUnknownValue(reportCounts.updated_rows ?? 0)],
                          ['No change', formatUnknownValue(reportCounts.no_change_rows ?? 0)],
                        ].map(([l, v]) => (
                          <div key={l as string} className={styles.clubResourceCountCard}>
                            <span className={styles.clubResourceCountLabel}>{l}</span>
                            <span className={styles.clubResourceCountValue}>{v}</span>
                          </div>
                        ))}
                      </div>
                      {getErrorSummaryMessage(selectedImportJob) && (
                        <div className={styles.clubResourceErrorPanel}>
                          <div className={styles.clubResourceWarningTitle}>Summary</div>
                          <div>{getErrorSummaryMessage(selectedImportJob)}</div>
                        </div>
                      )}
                      {reportErrors.length > 0 && (
                        <div className={styles.clubResourceErrorPanel}>
                          <div className={styles.clubResourceWarningTitle}>Report errors</div>
                          <ul className={styles.clubResourceWarningList}>
                            {reportErrors.map((re, i) => {
                              const details = asRecord(re.details);
                              const missing = asArray<string>(details.missing_required_headers);
                              const groups = asArray<unknown>(details.missing_header_groups);
                              const dups = asArray<string>(details.duplicate_headers);
                              return (
                                <li key={i}>
                                  <div>{formatUnknownValue(asRecord(re).message)}</div>
                                  {missing.length > 0 && <div className={styles.clubResourceErrorDetail}>Missing required columns: <strong>{missing.join(', ')}</strong></div>}
                                  {groups.map((g, gi) => <div key={gi} className={styles.clubResourceErrorDetail}>At least one required: <strong>{asArray<string>(g).join(', ')}</strong></div>)}
                                  {dups.length > 0 && <div className={styles.clubResourceErrorDetail}>Duplicates: <strong>{dups.join(', ')}</strong></div>}
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {viewerResource && viewerUrl && (
        <div className={styles.clubResourceViewerOverlay} role="dialog" aria-modal="true">
          <div className={styles.clubResourceViewerCard}>
            <div className={styles.clubResourceViewerHead}>
              <div>
                <h3 className={styles.clubResourceViewerTitle}>{viewerResource.title}</h3>
                <p className={styles.clubResourceViewerSub}>{viewerResource.original_filename}</p>
              </div>
              <div className={styles.clubResourceViewerHeadActions}>
                <button className={styles.clubResourceGhostBtn} type="button" disabled={!viewerResource || !viewerUrl || viewerLoading} onClick={() => viewerResource && handleDownloadResource(viewerResource)}>Download</button>
                <button className={styles.clubResourceGhostBtn} type="button" onClick={() => void handleCloseViewer()}>✕ Close</button>
              </div>
            </div>
            {viewerError && <div className={styles.clubResourceError}>{viewerError}</div>}
            <div className={styles.clubResourceViewerControls}>
              <button className={styles.clubResourceGhostBtn} type="button" disabled={viewerPage <= 1} onClick={() => setViewerPage((p) => Math.max(1, p - 1))}>← Previous</button>
              <span className={styles.clubResourceViewerPageIndicator}>Page {viewerPage}{viewerPageCount ? ` of ${viewerPageCount}` : ''}</span>
              <button className={styles.clubResourceGhostBtn} type="button" disabled={viewerPageCount === 0 || viewerPage >= viewerPageCount} onClick={() => setViewerPage((p) => viewerPageCount ? Math.min(viewerPageCount, p + 1) : p + 1)}>Next →</button>
            </div>
            <div className={styles.clubResourceViewerBody}>
              <Document
                file={viewerFile}
                loading={<div className={styles.clubResourceEmpty}>Loading PDF…</div>}
                onLoadSuccess={({ numPages }) => { setViewerPageCount(numPages); setViewerPage(1); currentPageRef.current = 1; }}
                onLoadError={() => setViewerError('Failed to render PDF preview.')}
                className={styles.clubResourceViewerDoc}
              >
                <Page pageNumber={viewerPage} width={760} renderAnnotationLayer={false} renderTextLayer={false} />
              </Document>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default ClubResourcesSection;