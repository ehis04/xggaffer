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
}

type ResourceStatusMap = Record<number, ClubResourceMyStatus>;

type UnknownRecord = Record<string, unknown>;

const ACCEPTED_RESOURCE_TYPES =
  '.pdf,.docx,.pptx,.xlsx,.csv,.png,.jpg,.jpeg,.webp';

const HEARTBEAT_INTERVAL_MS = 15000;

const IMPORT_TYPE_OPTIONS: Array<{
  value: ClubImportType;
  label: string;
  description: string;
}> = [
  {
    value: 'player_profile_update',
    label: 'Player profile update',
    description: 'Update club-local ClubPlayer fields such as display name, number, position, or height.',
  },
  {
    value: 'player_season_stats',
    label: 'Player season stats',
    description: 'Create or update season-level player enrichment rows for linked canonical players.',
  },
  {
    value: 'squad_metrics',
    label: 'Squad metrics',
    description: 'Create or update season-level club enrichment rows such as wins, goals, xG, and PPDA.',
  },
];

const getFileKindLabel = (resource: ClubResource): string => {
  switch (resource.file_kind) {
    case 'pdf':
      return 'PDF';
    case 'docx':
      return 'DOCX';
    case 'pptx':
      return 'PPTX';
    case 'xlsx':
      return 'XLSX';
    case 'csv':
      return 'CSV';
    case 'image':
      return 'Image';
    default:
      return 'File';
  }
};

const getVisibilityLabel = (value: ClubResourceEngagementVisibility): string => {
  return value === 'club_visible' ? 'Club visible' : 'Staff only';
};

const getImportTypeLabel = (value: ClubImportType): string => {
  return (
    IMPORT_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value
  );
};

const getImportStatusLabel = (value: string): string => {
  switch (value) {
    case 'uploaded':
      return 'Uploaded';
    case 'validating':
      return 'Validating';
    case 'preview_ready':
      return 'Preview ready';
    case 'confirmed':
      return 'Confirmed';
    case 'processing':
      return 'Processing';
    case 'completed':
      return 'Completed';
    case 'failed':
      return 'Failed';
    case 'cancelled':
      return 'Cancelled';
    default:
      return value;
  }
};

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDateTime = (value: string | null): string | null => {
  if (!value) {
    return null;
  }

  return new Date(value).toLocaleString('en-IE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getMyStatusLabel = (status: ClubResourceMyStatus | undefined): string => {
  if (!status?.my_view_summary) {
    return 'Not opened';
  }

  if (status.my_view_summary.completed) {
    return 'Completed';
  }

  if (status.my_view_summary.opened) {
    return 'Opened';
  }

  return 'Not opened';
};

const asRecord = (value: unknown): UnknownRecord => {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as UnknownRecord)
    : {};
};

const asArray = <T,>(value: unknown): T[] => {
  return Array.isArray(value) ? (value as T[]) : [];
};

const formatUnknownValue = (value: unknown): string => {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  if (typeof value === 'string') {
    return value;
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  if (Array.isArray(value)) {
    return value.map((item) => formatUnknownValue(item)).join(', ');
  }

  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

const getPreviewCounts = (job: ClubImportJob | null): UnknownRecord => {
  return asRecord(asRecord(job?.preview_payload).counts);
};

const getReportCounts = (job: ClubImportJob | null): UnknownRecord => {
  return asRecord(asRecord(job?.report_payload).counts);
};

const getPreviewRows = (job: ClubImportJob | null): UnknownRecord[] => {
  return asArray<UnknownRecord>(asRecord(job?.preview_payload).rows);
};

const getReportErrors = (job: ClubImportJob | null): UnknownRecord[] => {
  return asArray<UnknownRecord>(asRecord(job?.report_payload).errors);
};

const getErrorSummaryMessage = (job: ClubImportJob | null): string | null => {
  const summary = asRecord(job?.error_summary);
  const message = summary.message;
  return typeof message === 'string' && message.trim() ? message : null;
};

export const ClubResourcesSection = ({
  club,
  isMember,
}: ClubResourcesSectionProps) => {
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
  const [uploadVisibility, setUploadVisibility] =
    useState<ClubResourceEngagementVisibility>('staff_only');
  const [uploading, setUploading] = useState(false);

  const [resourceActionMessage, setResourceActionMessage] = useState<string | null>(null);

  const [selectedEngagement, setSelectedEngagement] =
    useState<ClubResourceEngagement | null>(null);
  const [selectedEngagementResourceId, setSelectedEngagementResourceId] =
    useState<number | null>(null);
  const [engagementLoading, setEngagementLoading] = useState(false);

  const [viewerResource, setViewerResource] = useState<ClubResource | null>(null);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);
  const [viewerLoading, setViewerLoading] = useState(false);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [viewerPage, setViewerPage] = useState(1);
  const [viewerPageCount, setViewerPageCount] = useState(0);

  const [canAccessImports, setCanAccessImports] = useState(false);
  const [importJobs, setImportJobs] = useState<ClubImportJobListItem[]>([]);
  const [importLoading, setImportLoading] = useState(false);
  const [selectedImportJob, setSelectedImportJob] = useState<ClubImportJob | null>(null);
  const [selectedResourceId, setSelectedResourceId] = useState<number | null>(null);
  const [selectedImportType, setSelectedImportType] =
    useState<ClubImportType>('player_profile_update');
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [creatingPreview, setCreatingPreview] = useState(false);
  const [loadingImportDetail, setLoadingImportDetail] = useState(false);
  const [committingImport, setCommittingImport] = useState(false);

  const currentPageRef = useRef(1);
  const activeViewerResourceRef = useRef<ClubResource | null>(null);
  const lastHeartbeatAtRef = useRef<number | null>(null);

  const importableResources = useMemo(
    () =>
      resources.filter(
        (resource) =>
          !resource.is_archived &&
          (resource.file_kind === 'csv' || resource.file_kind === 'xlsx'),
      ),
    [resources],
  );

  useEffect(() => {
    if (!selectedResourceId && importableResources.length > 0) {
      setSelectedResourceId(importableResources[0].id);
    }

    if (
      selectedResourceId &&
      !importableResources.some((resource) => resource.id === selectedResourceId)
    ) {
      setSelectedResourceId(importableResources[0]?.id ?? null);
    }
  }, [importableResources, selectedResourceId]);

  const loadStatuses = useCallback(
    async (resourceList: ClubResource[]) => {
      if (!isMember || resourceList.length === 0) {
        setResourceStatuses({});
        return;
      }

      const statusEntries = await Promise.all(
        resourceList.map(async (resource) => {
          try {
            const status = await clubsApi.getMyResourceStatus(club.id, resource.id);
            return [resource.id, status] as const;
          } catch {
            return [resource.id, null] as const;
          }
        }),
      );

      const nextStatuses: ResourceStatusMap = {};
      statusEntries.forEach(([resourceId, status]) => {
        if (status) {
          nextStatuses[resourceId] = status;
        }
      });

      setResourceStatuses(nextStatuses);
    },
    [club.id, isMember],
  );

  const loadResources = useCallback(async () => {
    if (!isMember) {
      setResources([]);
      setResourceStatuses({});
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const resourceList = await clubsApi.listResources(club.id);
      setResources(resourceList);
      await loadStatuses(resourceList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load club resources.');
    } finally {
      setLoading(false);
    }
  }, [club.id, isMember, loadStatuses]);

  const loadImportJobs = useCallback(async () => {
    if (!isMember) {
      setCanAccessImports(false);
      setImportJobs([]);
      setSelectedImportJob(null);
      return;
    }

    try {
      setImportLoading(true);
      const jobs = await clubsApi.listImportJobs(club.id);
      setImportJobs(jobs);
      setCanAccessImports(true);
    } catch {
      setCanAccessImports(false);
      setImportJobs([]);
      setSelectedImportJob(null);
    } finally {
      setImportLoading(false);
    }
  }, [club.id, isMember]);

  useEffect(() => {
    void loadResources();
    void loadImportJobs();
  }, [loadResources, loadImportJobs]);

  const sendHeartbeat = useCallback(
    async (resourceId: number, activeSecondsDelta: number, pageReached: number | null) => {
      await clubsApi.sendResourceHeartbeat(club.id, resourceId, {
        active_seconds_delta: activeSecondsDelta,
        page_reached: pageReached,
      });
    },
    [club.id],
  );

  const flushPdfHeartbeat = useCallback(() => {
    const activeResource = activeViewerResourceRef.current;
    const lastHeartbeatAt = lastHeartbeatAtRef.current;

    if (!activeResource || !lastHeartbeatAt) {
      return;
    }

    const elapsedSeconds = Math.max(
      0,
      Math.floor((Date.now() - lastHeartbeatAt) / 1000),
    );

    if (elapsedSeconds > 0) {
      void sendHeartbeat(activeResource.id, elapsedSeconds, currentPageRef.current)
        .then(() => clubsApi.getMyResourceStatus(club.id, activeResource.id))
        .then((status) => {
          setResourceStatuses((current) => ({
            ...current,
            [activeResource.id]: status,
          }));
        })
        .catch(() => {
          return;
        });
    }

    lastHeartbeatAtRef.current = Date.now();
  }, [club.id, sendHeartbeat]);

  useEffect(() => {
    if (!viewerResource || !viewerUrl || !viewerResource.can_inline_view) {
      return;
    }

    activeViewerResourceRef.current = viewerResource;
    currentPageRef.current = viewerPage;
    lastHeartbeatAtRef.current = Date.now();

    void sendHeartbeat(viewerResource.id, 0, viewerPage)
      .then(() => clubsApi.getMyResourceStatus(club.id, viewerResource.id))
      .then((status) => {
        setResourceStatuses((current) => ({
          ...current,
          [viewerResource.id]: status,
        }));
      })
      .catch(() => {
        return;
      });

    const intervalId = window.setInterval(() => {
      const lastHeartbeatAt = lastHeartbeatAtRef.current;
      if (!lastHeartbeatAt) {
        return;
      }

      const elapsedSeconds = Math.max(
        0,
        Math.floor((Date.now() - lastHeartbeatAt) / 1000),
      );

      if (elapsedSeconds <= 0) {
        return;
      }

      lastHeartbeatAtRef.current = Date.now();

      void sendHeartbeat(viewerResource.id, elapsedSeconds, currentPageRef.current)
        .then(() => clubsApi.getMyResourceStatus(club.id, viewerResource.id))
        .then((status) => {
          setResourceStatuses((current) => ({
            ...current,
            [viewerResource.id]: status,
          }));
        })
        .catch(() => {
          return;
        });
    }, HEARTBEAT_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
      flushPdfHeartbeat();
      activeViewerResourceRef.current = null;
    };
  }, [club.id, flushPdfHeartbeat, sendHeartbeat, viewerPage, viewerResource, viewerUrl]);

  useEffect(() => {
    currentPageRef.current = viewerPage;
  }, [viewerPage]);

  const handleUploadSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!uploadTitle.trim()) {
      setResourceActionMessage('Resource title is required.');
      return;
    }

    if (!uploadFile) {
      setResourceActionMessage('Choose a supported file before uploading.');
      return;
    }

    try {
      setUploading(true);
      setResourceActionMessage(null);

      await clubsApi.uploadResource(club.id, {
        title: uploadTitle.trim(),
        description: uploadDescription.trim(),
        file: uploadFile,
        engagement_visibility: uploadVisibility,
      });

      setUploadTitle('');
      setUploadDescription('');
      setUploadFile(null);
      setUploadVisibility('staff_only');
      setResourceActionMessage('Resource uploaded successfully.');
      await loadResources();
    } catch (err) {
      setResourceActionMessage(
        err instanceof Error
          ? err.message
          : 'Upload failed. Only owner/admin/coach members can upload resources.',
      );
    } finally {
      setUploading(false);
    }
  };

  const handleOpenResource = async (resource: ClubResource) => {
    try {
      setResourceActionMessage(null);
      setViewerError(null);
      setViewerLoading(true);

      const access = await clubsApi.getResourceAccess(club.id, resource.id);

      if (resource.can_inline_view) {
        setViewerResource(resource);
        setViewerUrl(access.access_url);
        setViewerPage(1);
        setViewerPageCount(0);
      } else {
        await clubsApi.sendResourceHeartbeat(club.id, resource.id, {
          active_seconds_delta: 0,
          page_reached: null,
        });

        const latestStatus = await clubsApi.getMyResourceStatus(club.id, resource.id);
        setResourceStatuses((current) => ({
          ...current,
          [resource.id]: latestStatus,
        }));

        window.open(access.access_url, '_blank', 'noopener,noreferrer');
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to open this resource.';
      setViewerError(message);
      setResourceActionMessage(message);
    } finally {
      setViewerLoading(false);
    }
  };

  const handleCloseViewer = async () => {
    flushPdfHeartbeat();

    if (viewerResource) {
      try {
        const latestStatus = await clubsApi.getMyResourceStatus(club.id, viewerResource.id);
        setResourceStatuses((current) => ({
          ...current,
          [viewerResource.id]: latestStatus,
        }));
      } catch {
        return;
      }
    }

    setViewerResource(null);
    setViewerUrl(null);
    setViewerPage(1);
    setViewerPageCount(0);
    setViewerError(null);
    activeViewerResourceRef.current = null;
    lastHeartbeatAtRef.current = null;
  };

  const handleLoadEngagement = async (resource: ClubResource) => {
    try {
      setEngagementLoading(true);
      setResourceActionMessage(null);

      const engagement = await clubsApi.getResourceEngagement(club.id, resource.id);
      setSelectedEngagement(engagement);
      setSelectedEngagementResourceId(resource.id);
    } catch (err) {
      setSelectedEngagement(null);
      setSelectedEngagementResourceId(resource.id);
      setResourceActionMessage(
        err instanceof Error
          ? err.message
          : 'Detailed engagement is only available to authorised club staff.',
      );
    } finally {
      setEngagementLoading(false);
    }
  };

  const handleCreateImportPreview = async () => {
    if (!selectedResourceId) {
      setImportMessage('Select a CSV or XLSX resource first.');
      return;
    }

    try {
      setCreatingPreview(true);
      setImportMessage(null);

      const job = await clubsApi.createImportJob(club.id, {
        source_resource: selectedResourceId,
        import_type: selectedImportType,
      });

      setSelectedImportJob(job);
      await loadImportJobs();

      if (job.status === 'preview_ready') {
        setImportMessage('Preview created successfully.');
      } else if (job.status === 'failed') {
        setImportMessage('Import preview failed. Review the report below.');
      } else {
        setImportMessage(`Import job created with status: ${getImportStatusLabel(job.status)}.`);
      }
    } catch (err) {
      setImportMessage(
        err instanceof Error ? err.message : 'Failed to create import preview.',
      );
    } finally {
      setCreatingPreview(false);
    }
  };

  const handleSelectImportJob = async (jobId: number) => {
    try {
      setLoadingImportDetail(true);
      setImportMessage(null);
      const detail = await clubsApi.getImportJob(club.id, jobId);
      setSelectedImportJob(detail);
    } catch (err) {
      setImportMessage(
        err instanceof Error ? err.message : 'Failed to load import job details.',
      );
    } finally {
      setLoadingImportDetail(false);
    }
  };

  const handleCommitImport = async () => {
    if (!selectedImportJob) {
      return;
    }

    const confirmed = window.confirm(
      'This will commit the matched preview rows to the database. Continue?',
    );
    if (!confirmed) {
      return;
    }

    try {
      setCommittingImport(true);
      setImportMessage(null);

      const committedJob = await clubsApi.commitImportJob(club.id, selectedImportJob.id, {
        confirm: true,
      });

      setSelectedImportJob(committedJob);
      await loadImportJobs();
      setImportMessage(
        committedJob.status === 'completed'
          ? 'Import committed successfully.'
          : `Commit finished with status: ${getImportStatusLabel(committedJob.status)}.`,
      );
    } catch (err) {
      setImportMessage(
        err instanceof Error ? err.message : 'Failed to commit import job.',
      );
    } finally {
      setCommittingImport(false);
    }
  };

  const previewCounts = getPreviewCounts(selectedImportJob);
  const previewRows = getPreviewRows(selectedImportJob);
  const reportCounts = getReportCounts(selectedImportJob);
  const reportErrors = getReportErrors(selectedImportJob);
  const selectedImportOption = IMPORT_TYPE_OPTIONS.find(
    (option) => option.value === selectedImportType,
  );

  if (!isMember) {
    return (
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2 className={styles.title}>Club Resources</h2>
            <p className={styles.subtitle}>
              Resources become available once you are an active member of the club.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.title}>Club Resources</h2>
          <p className={styles.subtitle}>
            Upload learning material, analysis packs, spreadsheets, and other club files.
          </p>
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}
      {resourceActionMessage && <div className={styles.message}>{resourceActionMessage}</div>}

      <div className={styles.grid}>
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Upload resource</h3>
          <p className={styles.cardSubtitle}>
            Coaches and authorised staff can upload PDFs, Word, PowerPoint, Excel, CSV, and images.
          </p>

          <form className={styles.form} onSubmit={handleUploadSubmit}>
            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor={uploadTitleInputId}>
                Title
              </label>
              <input
                id={uploadTitleInputId}
                className={styles.input}
                type="text"
                value={uploadTitle}
                onChange={(event) => setUploadTitle(event.target.value)}
                placeholder="e.g. Matchday analysis pack"
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor={uploadDescriptionInputId}>
                Description
              </label>
              <textarea
                id={uploadDescriptionInputId}
                className={styles.textarea}
                rows={4}
                value={uploadDescription}
                onChange={(event) => setUploadDescription(event.target.value)}
                placeholder="Optional context for players and staff."
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor={uploadVisibilitySelectId}>
                Engagement visibility
              </label>
              <select
                id={uploadVisibilitySelectId}
                className={styles.select}
                value={uploadVisibility}
                onChange={(event) =>
                  setUploadVisibility(event.target.value as ClubResourceEngagementVisibility)
                }
              >
                <option value="staff_only">Staff only</option>
                <option value="club_visible">Club visible</option>
              </select>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label} htmlFor={uploadFileInputId}>
                File
              </label>
              <input
                id={uploadFileInputId}
                className={styles.fileInput}
                type="file"
                accept={ACCEPTED_RESOURCE_TYPES}
                onChange={(event) => {
                  setUploadFile(event.target.files?.[0] ?? null);
                }}
              />
              <p className={styles.helperText}>
                Supported formats: PDF, DOCX, PPTX, XLSX, CSV, PNG, JPG, JPEG, and WEBP.
              </p>
            </div>

            <div className={styles.actionRow}>
              <button
                className={styles.primaryButton}
                type="submit"
                disabled={uploading}
              >
                {uploading ? 'Uploading…' : 'Upload resource'}
              </button>
            </div>
          </form>
        </div>

        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Resource library</h3>
          <p className={styles.cardSubtitle}>
            Open club resources and review engagement where permitted.
          </p>

          {loading ? (
            <div className={styles.loading}>Loading club resources…</div>
          ) : resources.length === 0 ? (
            <div className={styles.emptyState}>No resources uploaded yet.</div>
          ) : (
            <div className={styles.resourceList}>
              {resources.map((resource) => {
                const myStatus = resourceStatuses[resource.id];

                return (
                  <div key={resource.id} className={styles.resourceCard}>
                    <div className={styles.resourceHeader}>
                      <div className={styles.resourceTitleGroup}>
                        <h4 className={styles.resourceTitle}>{resource.title}</h4>
                        <p className={styles.resourceSubtitle}>
                          {resource.original_filename}
                        </p>
                      </div>

                      <span className={styles.statusPill}>
                        {getFileKindLabel(resource)}
                      </span>
                    </div>

                    {resource.description && (
                      <p className={styles.resourceDescription}>{resource.description}</p>
                    )}

                    <div className={styles.metadataRow}>
                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>Size</span>
                        <span className={styles.metadataValue}>
                          {formatFileSize(resource.file_size_bytes)}
                        </span>
                      </div>

                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>Visibility</span>
                        <span className={styles.metadataValue}>
                          {getVisibilityLabel(resource.engagement_visibility)}
                        </span>
                      </div>

                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>Mode</span>
                        <span className={styles.metadataValue}>
                          {resource.can_inline_view ? 'Inline PDF' : 'Open / download'}
                        </span>
                      </div>

                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>Your status</span>
                        <span className={styles.metadataValue}>
                          {getMyStatusLabel(myStatus)}
                        </span>
                      </div>
                    </div>

                    <div className={styles.metadataRow}>
                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>Uploaded</span>
                        <span className={styles.metadataValue}>
                          {formatDateTime(resource.created_at) ?? '—'}
                        </span>
                      </div>

                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>Opened count</span>
                        <span className={styles.metadataValue}>
                          {myStatus?.opened_count ?? resource.opened_count ?? 0}
                        </span>
                      </div>

                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>Completed count</span>
                        <span className={styles.metadataValue}>
                          {myStatus?.completed_count ?? resource.completed_count ?? 0}
                        </span>
                      </div>

                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>Last opened</span>
                        <span className={styles.metadataValue}>
                          {formatDateTime(
                            myStatus?.my_view_summary?.last_opened_at ?? resource.latest_opened_at,
                          ) ?? '—'}
                        </span>
                      </div>
                    </div>

                    <div className={styles.actionRow}>
                      <button
                        className={styles.primaryButton}
                        type="button"
                        disabled={viewerLoading}
                        onClick={() => handleOpenResource(resource)}
                      >
                        {resource.can_inline_view ? 'Open PDF' : 'Open / Download'}
                      </button>

                      <button
                        className={styles.secondaryButton}
                        type="button"
                        disabled={engagementLoading}
                        onClick={() => handleLoadEngagement(resource)}
                      >
                        {selectedEngagementResourceId === resource.id && engagementLoading
                          ? 'Loading…'
                          : 'View engagement'}
                      </button>
                    </div>

                    {selectedEngagementResourceId === resource.id && selectedEngagement && (
                      <div className={styles.engagementPanel}>
                        <div className={styles.engagementSummary}>
                          <span>Total viewers: {selectedEngagement.total_viewers}</span>
                          <span>Opened: {selectedEngagement.opened_count}</span>
                          <span>Completed: {selectedEngagement.completed_count}</span>
                        </div>

                        {selectedEngagement.resource_views.length === 0 ? (
                          <div className={styles.emptyState}>No engagement recorded yet.</div>
                        ) : (
                          <div className={styles.engagementTableWrapper}>
                            <table className={styles.engagementTable}>
                              <thead>
                                <tr>
                                  <th>User</th>
                                  <th>Opened</th>
                                  <th>Completed</th>
                                  <th>Active seconds</th>
                                  <th>Highest page</th>
                                  <th>Last opened</th>
                                </tr>
                              </thead>
                              <tbody>
                                {selectedEngagement.resource_views.map((viewRow) => (
                                  <tr key={viewRow.id}>
                                    <td>{viewRow.user_email}</td>
                                    <td>{viewRow.opened ? 'Yes' : 'No'}</td>
                                    <td>{viewRow.completed ? 'Yes' : 'No'}</td>
                                    <td>{viewRow.total_active_seconds}</td>
                                    <td>{viewRow.highest_page_reached}</td>
                                    <td>{formatDateTime(viewRow.last_opened_at) ?? '—'}</td>
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
      </div>

      {canAccessImports && (
        <div className={styles.importSection}>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Structured imports</h3>
            <p className={styles.cardSubtitle}>
              Create a preview from a CSV/XLSX resource, review the matched rows, then explicitly confirm the commit.
            </p>

            {importMessage && <div className={styles.message}>{importMessage}</div>}

            <div className={styles.importBuilder}>
              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor={importResourceSelectId}>
                  Source resource
                </label>
                <select
                  id={importResourceSelectId}
                  className={styles.select}
                  value={selectedResourceId ?? ''}
                  onChange={(event) => setSelectedResourceId(Number(event.target.value) || null)}
                >
                  {importableResources.length === 0 ? (
                    <option value="">No CSV/XLSX resources available</option>
                  ) : (
                    <>
                      <option value="">Select a resource</option>
                      {importableResources.map((resource) => (
                        <option key={resource.id} value={resource.id}>
                          {resource.title} · {resource.original_filename}
                        </option>
                      ))}
                    </>
                  )}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label} htmlFor={importTypeSelectId}>
                  Import type
                </label>
                <select
                  id={importTypeSelectId}
                  className={styles.select}
                  value={selectedImportType}
                  onChange={(event) =>
                    setSelectedImportType(event.target.value as ClubImportType)
                  }
                >
                  {IMPORT_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <p className={styles.helperText}>
                  {selectedImportOption?.description}
                </p>
              </div>

              <div className={styles.actionRow}>
                <button
                  type="button"
                  className={styles.primaryButton}
                  disabled={creatingPreview || !selectedResourceId}
                  onClick={() => void handleCreateImportPreview()}
                >
                  {creatingPreview ? 'Creating preview…' : 'Create preview'}
                </button>
              </div>
            </div>

            <div className={styles.importGrid}>
              <div className={styles.importHistory}>
                <div className={styles.importHistoryHeader}>
                  <h4 className={styles.importHistoryTitle}>Import history</h4>
                  {importLoading && <span className={styles.mutedText}>Loading…</span>}
                </div>

                {importJobs.length === 0 ? (
                  <div className={styles.emptyState}>
                    No import jobs yet.
                  </div>
                ) : (
                  <div className={styles.importJobList}>
                    {importJobs.map((job) => {
                      const isSelected = selectedImportJob?.id === job.id;

                      return (
                        <button
                          key={job.id}
                          type="button"
                          className={`${styles.importJobCard} ${isSelected ? styles.importJobCardSelected : ''}`}
                          onClick={() => void handleSelectImportJob(job.id)}
                        >
                          <div className={styles.importJobHeader}>
                            <div>
                              <div className={styles.importJobTitle}>
                                {getImportTypeLabel(job.import_type)}
                              </div>
                              <div className={styles.importJobMeta}>
                                {job.source_resource_original_filename}
                              </div>
                            </div>
                            <span className={`${styles.previewBadge} ${styles[`status_${job.status}`] ?? ''}`}>
                              {getImportStatusLabel(job.status)}
                            </span>
                          </div>

                          <div className={styles.importJobMeta}>
                            {job.valid_row_count} valid · {job.warning_count} warnings
                          </div>
                          <div className={styles.importJobMeta}>
                            Created {formatDateTime(job.created_at) ?? '—'}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className={styles.importDetail}>
                {loadingImportDetail ? (
                  <div className={styles.loading}>Loading import details…</div>
                ) : !selectedImportJob ? (
                  <div className={styles.emptyState}>
                    Select an import job to review its preview or final report.
                  </div>
                ) : (
                  <div className={styles.selectedJobCard}>
                    <div className={styles.selectedJobHeader}>
                      <div>
                        <h4 className={styles.selectedJobTitle}>
                          {getImportTypeLabel(selectedImportJob.import_type)}
                        </h4>
                        <p className={styles.selectedJobSubtitle}>
                          {selectedImportJob.source_resource_original_filename}
                        </p>
                      </div>

                      <span className={`${styles.previewBadge} ${styles[`status_${selectedImportJob.status}`] ?? ''}`}>
                        {getImportStatusLabel(selectedImportJob.status)}
                      </span>
                    </div>

                    <div className={styles.previewCounts}>
                      <div className={styles.countCard}>
                        <span className={styles.countLabel}>Total rows</span>
                        <span className={styles.countValue}>
                          {formatUnknownValue(previewCounts.total_rows ?? reportCounts.total_rows ?? 0)}
                        </span>
                      </div>
                      <div className={styles.countCard}>
                        <span className={styles.countLabel}>Valid rows</span>
                        <span className={styles.countValue}>
                          {formatUnknownValue(previewCounts.valid_rows ?? reportCounts.valid_rows ?? 0)}
                        </span>
                      </div>
                      <div className={styles.countCard}>
                        <span className={styles.countLabel}>Warnings</span>
                        <span className={styles.countValue}>
                          {formatUnknownValue(previewCounts.warning_count ?? selectedImportJob.warning_count)}
                        </span>
                      </div>
                      <div className={styles.countCard}>
                        <span className={styles.countLabel}>Imported</span>
                        <span className={styles.countValue}>
                          {formatUnknownValue(reportCounts.imported_rows ?? selectedImportJob.imported_row_count)}
                        </span>
                      </div>
                      <div className={styles.countCard}>
                        <span className={styles.countLabel}>Skipped</span>
                        <span className={styles.countValue}>
                          {formatUnknownValue(reportCounts.skipped_rows ?? selectedImportJob.skipped_row_count)}
                        </span>
                      </div>
                      <div className={styles.countCard}>
                        <span className={styles.countLabel}>Failed</span>
                        <span className={styles.countValue}>
                          {formatUnknownValue(reportCounts.failed_rows ?? selectedImportJob.failed_row_count)}
                        </span>
                      </div>
                    </div>

                    {selectedImportJob.status === 'preview_ready' && (
                      <div className={styles.commitBar}>
                        <div className={styles.commitText}>
                          Review the preview carefully before confirming the final commit.
                        </div>
                        <button
                          type="button"
                          className={styles.commitButton}
                          disabled={committingImport}
                          onClick={() => void handleCommitImport()}
                        >
                          {committingImport ? 'Committing…' : 'Confirm and commit'}
                        </button>
                      </div>
                    )}

                    {previewRows.length > 0 && (
                      <div className={styles.previewSection}>
                        <h5 className={styles.subsectionTitle}>Preview rows</h5>
                        <div className={styles.previewRowList}>
                          {previewRows.slice(0, 10).map((row) => {
                            const rowNumber = row.row_number;
                            const rowStatus = typeof row.status === 'string' ? row.status : 'unknown';
                            const warnings = asArray<string>(row.warnings);
                            const errors = asArray<string>(row.errors);
                            const currentValues = asRecord(row.current_values);
                            const proposedChanges = asRecord(row.proposed_changes);

                            return (
                              <div
                                key={typeof rowNumber === 'number' ? rowNumber : Math.random()}
                                className={styles.previewRowCard}
                              >
                                <div className={styles.previewRowHeader}>
                                  <div>
                                    <div className={styles.previewRowTitle}>
                                      Row {formatUnknownValue(rowNumber)}
                                    </div>
                                    <div className={styles.previewRowMeta}>
                                      {formatUnknownValue(row.target_label)} · {formatUnknownValue(row.match_method)}
                                    </div>
                                  </div>

                                  <span className={`${styles.previewBadge} ${styles[`status_${rowStatus}`] ?? ''}`}>
                                    {rowStatus}
                                  </span>
                                </div>

                                <div className={styles.previewColumns}>
                                  <div className={styles.previewColumn}>
                                    <h6 className={styles.previewColumnTitle}>Current values</h6>
                                    {Object.keys(currentValues).length === 0 ? (
                                      <div className={styles.mutedText}>No existing values shown.</div>
                                    ) : (
                                      <div className={styles.keyValueList}>
                                        {Object.entries(currentValues).map(([key, value]) => (
                                          <div key={key} className={styles.keyValueItem}>
                                            <span className={styles.keyValueKey}>{key}</span>
                                            <span className={styles.keyValueValue}>
                                              {formatUnknownValue(value)}
                                            </span>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>

                                  <div className={styles.previewColumn}>
                                    <h6 className={styles.previewColumnTitle}>Proposed changes</h6>
                                    {Object.keys(proposedChanges).length === 0 ? (
                                      <div className={styles.mutedText}>No changes proposed.</div>
                                    ) : (
                                      <div className={styles.changesList}>
                                        {Object.entries(proposedChanges).map(([key, value]) => {
                                          const change = asRecord(value);

                                          return (
                                            <div key={key} className={styles.changeItem}>
                                              <div className={styles.changeKey}>{key}</div>
                                              <div className={styles.changeValues}>
                                                <span>{formatUnknownValue(change.from)}</span>
                                                <span className={styles.changeArrow}>→</span>
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
                                  <div className={styles.warningPanel}>
                                    <h6 className={styles.warningTitle}>Warnings</h6>
                                    <ul className={styles.warningList}>
                                      {warnings.map((warning, index) => (
                                        <li key={`${warning}-${index}`}>{warning}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {errors.length > 0 && (
                                  <div className={styles.errorPanel}>
                                    <h6 className={styles.errorTitle}>Errors</h6>
                                    <ul className={styles.errorList}>
                                      {errors.map((rowError, index) => (
                                        <li key={`${rowError}-${index}`}>{rowError}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>

                        {previewRows.length > 10 && (
                          <div className={styles.mutedText}>
                            Showing the first 10 preview rows. Use the job detail payload for the full persisted preview.
                          </div>
                        )}
                      </div>
                    )}

                    {(selectedImportJob.status === 'completed' || selectedImportJob.status === 'failed') && (
                      <div className={styles.reportPanel}>
                        <h5 className={styles.subsectionTitle}>Final report</h5>

                        <div className={styles.reportGrid}>
                          <div className={styles.countCard}>
                            <span className={styles.countLabel}>Created</span>
                            <span className={styles.countValue}>
                              {formatUnknownValue(reportCounts.created_rows ?? 0)}
                            </span>
                          </div>
                          <div className={styles.countCard}>
                            <span className={styles.countLabel}>Updated</span>
                            <span className={styles.countValue}>
                              {formatUnknownValue(reportCounts.updated_rows ?? 0)}
                            </span>
                          </div>
                          <div className={styles.countCard}>
                            <span className={styles.countLabel}>No change</span>
                            <span className={styles.countValue}>
                              {formatUnknownValue(reportCounts.no_change_rows ?? 0)}
                            </span>
                          </div>
                        </div>

                        {getErrorSummaryMessage(selectedImportJob) && (
                          <div className={styles.errorPanel}>
                            <h6 className={styles.errorTitle}>Summary</h6>
                            <div>{getErrorSummaryMessage(selectedImportJob)}</div>
                          </div>
                        )}

                        {reportErrors.length > 0 && (
                          <div className={styles.errorPanel}>
                            <h6 className={styles.errorTitle}>Report errors</h6>
                            <ul className={styles.errorList}>
                              {reportErrors.map((reportError, index) => {
                                const details = asRecord(reportError.details);
                                const missingRequired = asArray<string>(details.missing_required_headers);
                                const missingGroups = asArray<unknown>(details.missing_header_groups);
                                const duplicates = asArray<string>(details.duplicate_headers);
                                return (
                                  <li key={index}>
                                    <div>{formatUnknownValue(asRecord(reportError).message)}</div>
                                    {missingRequired.length > 0 && (
                                      <div className={styles.errorDetail}>
                                        Missing required columns: <strong>{missingRequired.join(', ')}</strong>
                                      </div>
                                    )}
                                    {missingGroups.map((group, gi) => (
                                      <div key={gi} className={styles.errorDetail}>
                                        At least one of these columns is required: <strong>{asArray<string>(group).join(', ')}</strong>
                                      </div>
                                    ))}
                                    {duplicates.length > 0 && (
                                      <div className={styles.errorDetail}>
                                        Duplicate columns: <strong>{duplicates.join(', ')}</strong>
                                      </div>
                                    )}
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
        </div>
      )}

      {viewerResource && viewerUrl && (
        <div className={styles.viewerOverlay} role="dialog" aria-modal="true">
          <div className={styles.viewerCard}>
            <div className={styles.viewerHeader}>
              <div>
                <h3 className={styles.viewerTitle}>{viewerResource.title}</h3>
                <p className={styles.viewerSubtitle}>
                  {viewerResource.original_filename}
                </p>
              </div>

              <button
                type="button"
                className={styles.closeButton}
                onClick={() => void handleCloseViewer()}
              >
                Close
              </button>
            </div>

            {viewerError && <div className={styles.error}>{viewerError}</div>}

            <div className={styles.viewerControls}>
              <button
                type="button"
                className={styles.secondaryButton}
                disabled={viewerPage <= 1}
                onClick={() => setViewerPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </button>

              <div className={styles.pageIndicator}>
                Page {viewerPage}{viewerPageCount ? ` of ${viewerPageCount}` : ''}
              </div>

              <button
                type="button"
                className={styles.secondaryButton}
                disabled={viewerPageCount === 0 || viewerPage >= viewerPageCount}
                onClick={() =>
                  setViewerPage((current) =>
                    viewerPageCount ? Math.min(viewerPageCount, current + 1) : current + 1,
                  )
                }
              >
                Next
              </button>
            </div>

            <div className={styles.viewerBody}>
              <Document
                file={viewerUrl}
                loading={<div className={styles.emptyState}>Loading PDF…</div>}
                onLoadSuccess={({ numPages }) => {
                  setViewerPageCount(numPages);
                  setViewerPage(1);
                  currentPageRef.current = 1;
                }}
                onLoadError={() => {
                  setViewerError('Failed to render PDF preview.');
                }}
                className={styles.document}
              >
                <Page
                  pageNumber={viewerPage}
                  width={760}
                  renderAnnotationLayer={false}
                  renderTextLayer={false}
                />
              </Document>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default ClubResourcesSection;