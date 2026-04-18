import { useEffect } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const clubsApiMock = vi.hoisted(() => ({
  listResources: vi.fn(),
  getMyResourceStatus: vi.fn(),
  uploadResource: vi.fn(),
  getResourceAccess: vi.fn(),
  sendResourceHeartbeat: vi.fn(),
  getResourceEngagement: vi.fn(),
}));

import type {
  Club,
  ClubResource,
  ClubResourceEngagement,
  ClubResourceMyStatus,
  ClubResourceSignedAccessResponse,
  ClubResourceViewSummary,
} from '../../../../../types/club';
import ClubResourcesSection from '../ClubResourcesSection';

vi.mock('../../../../../services/api', () => ({
  clubsApi: clubsApiMock,
}));

vi.mock('react-pdf', () => ({
  pdfjs: {
    GlobalWorkerOptions: {
      workerSrc: '',
    },
  },
  Document: ({
    children,
    onLoadSuccess,
  }: {
    children: React.ReactNode;
    onLoadSuccess?: (payload: { numPages: number }) => void;
  }) => {
    useEffect(() => {
      onLoadSuccess?.({ numPages: 3 });
    }, [onLoadSuccess]);

    return <div data-testid="mock-pdf-document">{children}</div>;
  },
  Page: ({ pageNumber }: { pageNumber: number }) => (
    <div data-testid="mock-pdf-page">PDF page {pageNumber}</div>
  ),
}));

const flushAsyncWork = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
};

const baseClub: Club = {
  id: 7,
  name: 'Resource Test Club',
  description: 'Club resources frontend tests.',
  badge: null,
  creator: 1,
  creator_username: 'owner@example.com',
  visibility: 'private',
  club_type: 'user_fictional',
  fictional_basis: 'original',
  source_real_club_name: '',
  directory_visibility: 'listed',
  join_policy: 'approval_required',
  join_code: null,
  verification_status: 'not_required',
  city: 'Dublin',
  country: 'IE',
  stadium: '',
  division: '',
  achievements: '',
  member_count: 10,
  player_count: 18,
  latest_understat_summary: null,
  is_trashed: false,
  trashed_at: null,
  trash_expires_at: null,
  trashed_by: null,
  created_at: '2026-04-01T10:00:00Z',
  updated_at: '2026-04-01T10:00:00Z',
};

const buildPdfResource = (): ClubResource => ({
  id: 11,
  club: 7,
  club_name: 'Resource Test Club',
  uploaded_by: 1,
  uploaded_by_email: 'owner@example.com',
  title: 'Analysis Pack',
  description: 'Detailed pre-match PDF.',
  original_filename: 'analysis-pack.pdf',
  mime_type: 'application/pdf',
  file_size_bytes: 2048,
  file_kind: 'pdf',
  engagement_visibility: 'club_visible',
  is_archived: false,
  total_pages: 3,
  viewer_mode: 'inline',
  can_inline_view: true,
  is_download_only: false,
  opened_count: 2,
  completed_count: 1,
  latest_opened_at: '2026-04-05T10:00:00Z',
  created_at: '2026-04-05T09:00:00Z',
  updated_at: '2026-04-05T09:00:00Z',
});

const buildStatus = (): ClubResourceMyStatus => ({
  resource_id: 11,
  engagement_visibility: 'club_visible',
  can_view_club_status: true,
  opened_count: 2,
  completed_count: 1,
  my_view_summary: {
    id: 201,
    resource: 11,
    user: 55,
    user_email: 'member@example.com',
    first_opened_at: '2026-04-05T09:20:00Z',
    last_opened_at: '2026-04-05T09:30:00Z',
    total_active_seconds: 45,
    highest_page_reached: 3,
    opened: true,
    completed: true,
    created_at: '2026-04-05T09:20:00Z',
    updated_at: '2026-04-05T09:30:00Z',
  },
});

describe('ClubResourcesSection', () => {
  beforeEach(() => {
    clubsApiMock.listResources.mockResolvedValue([buildPdfResource()]);
    clubsApiMock.getMyResourceStatus.mockResolvedValue(buildStatus());
    clubsApiMock.uploadResource.mockResolvedValue(buildPdfResource());
    clubsApiMock.getResourceAccess.mockResolvedValue({
      resource_id: 11,
      title: 'Analysis Pack',
      original_filename: 'analysis-pack.pdf',
      mime_type: 'application/pdf',
      file_kind: 'pdf',
      access_mode: 'inline',
      can_inline_view: true,
      is_download_only: false,
      access_url: 'https://example.com/signed/analysis-pack.pdf',
      expires_at: '2026-04-05T10:10:00Z',
    } satisfies ClubResourceSignedAccessResponse);
    clubsApiMock.sendResourceHeartbeat.mockResolvedValue({
      id: 201,
      resource: 11,
      user: 55,
      user_email: 'member@example.com',
      first_opened_at: '2026-04-05T09:20:00Z',
      last_opened_at: '2026-04-05T09:30:00Z',
      total_active_seconds: 30,
      highest_page_reached: 3,
      opened: true,
      completed: true,
      created_at: '2026-04-05T09:20:00Z',
      updated_at: '2026-04-05T09:30:00Z',
    } satisfies ClubResourceViewSummary);
    clubsApiMock.getResourceEngagement.mockResolvedValue({
      id: 11,
      title: 'Analysis Pack',
      engagement_visibility: 'club_visible',
      is_archived: false,
      total_viewers: 2,
      opened_count: 2,
      completed_count: 1,
      resource_views: [],
    } satisfies ClubResourceEngagement);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('validates upload form before calling upload api', async () => {
    render(<ClubResourcesSection club={baseClub} isMember canManageResources={true} />);

    await screen.findByText('Analysis Pack');

    fireEvent.click(screen.getByRole('button', { name: 'Upload resource' }));

    expect(
      screen.getByText('Resource title is required.')
    ).toBeInTheDocument();
    expect(clubsApiMock.uploadResource).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: 'New Pack' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Upload resource' }));

    expect(
      screen.getByText('Choose a supported file before uploading.')
    ).toBeInTheDocument();
    expect(clubsApiMock.uploadResource).not.toHaveBeenCalled();
  });

  it('renders status badges and member-visible engagement counts honestly', async () => {
    render(<ClubResourcesSection club={baseClub} isMember canManageResources={false} />);

    await screen.findByText('Analysis Pack');

    expect(screen.getByText('Club visible', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Opened count').length).toBeGreaterThan(0);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('sends heartbeat while a PDF is open', async () => {
    let intervalCallback: (() => void) | null = null;
    let now = 1_000;

    vi.spyOn(Date, 'now').mockImplementation(() => now);
    vi.spyOn(window, 'setInterval').mockImplementation((handler) => {
      intervalCallback = handler as () => void;
      return 1 as unknown as number;
    });
    vi.spyOn(window, 'clearInterval').mockImplementation(() => undefined);

    render(<ClubResourcesSection club={baseClub} isMember canManageResources={false} />);

    await screen.findByText('Analysis Pack');

    fireEvent.click(screen.getByRole('button', { name: 'Open PDF' }));

    await screen.findByTestId('mock-pdf-document');
    await flushAsyncWork();

    expect(clubsApiMock.getResourceAccess).toHaveBeenCalledWith(7, 11);

    expect(clubsApiMock.sendResourceHeartbeat).toHaveBeenCalledWith(7, 11, {
      active_seconds_delta: 0,
      page_reached: 1,
    });

    now = 16_000;

    await act(async () => {
      intervalCallback?.();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(clubsApiMock.sendResourceHeartbeat).toHaveBeenCalledWith(7, 11, {
      active_seconds_delta: 15,
      page_reached: 1,
    });
  });

  it('sends a final heartbeat when the viewer closes', async () => {
    let now = 1_000;

    vi.spyOn(Date, 'now').mockImplementation(() => now);
    vi.spyOn(window, 'setInterval').mockImplementation(() => {
      return 1 as unknown as number;
    });
    vi.spyOn(window, 'clearInterval').mockImplementation(() => undefined);

    render(<ClubResourcesSection club={baseClub} isMember canManageResources={false} />);

    await screen.findByText('Analysis Pack');

    fireEvent.click(screen.getByRole('button', { name: 'Open PDF' }));
    await screen.findByTestId('mock-pdf-document');
    await flushAsyncWork();

    now = 6_000;

    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    await flushAsyncWork();

    expect(clubsApiMock.sendResourceHeartbeat).toHaveBeenCalled();

    const finalCall = clubsApiMock.sendResourceHeartbeat.mock.calls.at(-1);
    expect(finalCall?.[0]).toBe(7);
    expect(finalCall?.[1]).toBe(11);
    expect(finalCall?.[2].page_reached).toBe(1);
    expect(finalCall?.[2].active_seconds_delta).toBeGreaterThanOrEqual(0);
  });
});