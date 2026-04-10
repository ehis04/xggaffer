import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { clubsApi } from '../../../services/api';
import type { Club, ClubJoinRequest } from '../../../types/club';
import { ClubCard } from '../../../components/Clubs';
import styles from './css/BrowseClubsPage.module.css';

const getRequestStatusLabel = (status: ClubJoinRequest['status']) => {
  switch (status) {
    case 'pending':
      return 'Pending review';
    case 'approved':
      return 'Approved';
    case 'rejected':
      return 'Rejected';
    case 'withdrawn':
      return 'Withdrawn';
    case 'cancelled':
      return 'Cancelled';
    default:
      return status;
  }
};

const BrowseClubsPage: React.FC = () => {
  const navigate = useNavigate();

  const [clubs, setClubs] = useState<Club[]>([]);
  const [myJoinRequests, setMyJoinRequests] = useState<ClubJoinRequest[]>([]);
  const [selectedClub, setSelectedClub] = useState<Club | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copyingId, setCopyingId] = useState<number | null>(null);
  const [requestingClubId, setRequestingClubId] = useState<number | null>(null);

  const [searchInput, setSearchInput] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [requestMessage, setRequestMessage] = useState('');
  const [workflowMessage, setWorkflowMessage] = useState<string | null>(null);

  const loadData = async (search?: string) => {
    try {
      setLoading(true);
      setError(null);

      const [clubsData, requestsData] = await Promise.all([
        clubsApi.browse(search ? { search } : undefined),
        clubsApi.listMyJoinRequests(),
      ]);

      setClubs(clubsData);
      setMyJoinRequests(requestsData);

      if (selectedClub) {
        const refreshedSelection = clubsData.find((club) => club.id === selectedClub.id) || null;
        setSelectedClub(refreshedSelection);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clubs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData(activeSearch);
  }, [activeSearch]);

  const visibleCountLabel = useMemo(() => {
    if (!activeSearch) {
      return `${clubs.length} listed clubs`;
    }

    return `${clubs.length} results for “${activeSearch}”`;
  }, [clubs.length, activeSearch]);

  const latestRequestForClub = (clubId: number) =>
    myJoinRequests.find((request) => request.club === clubId);

  const handleCopy = async (club: Club) => {
    if (copyingId) {
      return;
    }

    try {
      setCopyingId(club.id);
      setError(null);
      const newClub = await clubsApi.duplicate(club.id, { name: club.name });
      navigate(`/clubs/${newClub.id}/`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to copy club');
      setCopyingId(null);
    }
  };

  const handleSearchSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setActiveSearch(searchInput.trim());
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setActiveSearch('');
  };

  const handleSelectClub = (club: Club) => {
    setSelectedClub(club);
    setRequestMessage('');
    setWorkflowMessage(null);
  };

  const handleRequestToJoin = async (club: Club) => {
    try {
      setRequestingClubId(club.id);
      setWorkflowMessage(null);
      await clubsApi.requestToJoin(club.id, {
        requested_role: 'player',
        message: requestMessage.trim() || undefined,
      });

      setRequestMessage('');
      setWorkflowMessage('Join request submitted successfully.');
      const updatedRequests = await clubsApi.listMyJoinRequests();
      setMyJoinRequests(updatedRequests);
    } catch (err) {
      setWorkflowMessage(err instanceof Error ? err.message : 'Failed to submit join request.');
    } finally {
      setRequestingClubId(null);
    }
  };

  const renderWorkflowPanel = () => {
    if (!selectedClub) {
      return null;
    }

    const latestRequest = latestRequestForClub(selectedClub.id);
    const canSubmitFreshRequest =
      !latestRequest ||
      latestRequest.status === 'rejected' ||
      latestRequest.status === 'withdrawn' ||
      latestRequest.status === 'cancelled';

    return (
      <section className={styles.workflowPanel}>
        <div className={styles.workflowHeader}>
          <div>
            <h2 className={styles.panelTitle}>{selectedClub.name}</h2>
            <p className={styles.panelCopy}>
              Review the membership path for this listed club before you act.
            </p>
          </div>
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={() => setSelectedClub(null)}
          >
            Clear selection
          </button>
        </div>

        <div className={styles.workflowGrid}>
          <div className={styles.workflowCard}>
            <h3 className={styles.workflowTitle}>Membership path</h3>

            {selectedClub.join_policy === 'approval_required' && (
              <>
                <p className={styles.workflowText}>
                  This club accepts player join requests. Approval is still required even when the club is publicly listed.
                </p>

                {latestRequest && (
                  <div className={styles.statusBox}>
                    <span className={styles.statusLabel}>Your latest request</span>
                    <span className={styles.statusValue}>{getRequestStatusLabel(latestRequest.status)}</span>
                    {latestRequest.review_note && (
                      <p className={styles.statusNote}>Reviewer note: {latestRequest.review_note}</p>
                    )}
                  </div>
                )}

                {canSubmitFreshRequest ? (
                  <>
                    <textarea
                      className={styles.workflowTextarea}
                      value={requestMessage}
                      onChange={(event) => setRequestMessage(event.target.value)}
                      placeholder="Optional note to the club reviewer"
                      rows={4}
                    />
                    <button
                      className={styles.primaryButton}
                      type="button"
                      disabled={requestingClubId === selectedClub.id}
                      onClick={() => handleRequestToJoin(selectedClub)}
                    >
                      {requestingClubId === selectedClub.id ? 'Submitting...' : 'Request to Join'}
                    </button>
                  </>
                ) : (
                  <div className={styles.noticeBlock}>
                    A fresh request is not available while your current request is still active.
                  </div>
                )}
              </>
            )}

            {selectedClub.join_policy === 'invite_only' && (
              <div className={styles.noticeBlock}>
                This club is invite only. No self-service request flow is available from browse.
              </div>
            )}

            {selectedClub.join_policy === 'system_managed' && (
              <div className={styles.noticeBlock}>
                This club is system managed and is not claimable through ordinary membership workflows.
              </div>
            )}

            {workflowMessage && (
              <div className={styles.inlineMessage}>{workflowMessage}</div>
            )}
          </div>

          <div className={styles.workflowCard}>
            <h3 className={styles.workflowTitle}>What you are looking at</h3>
            <ul className={styles.infoList}>
              <li>Listed clubs appear in browse and search.</li>
              <li>Approval-required clubs route you into a real request flow.</li>
              <li>Invite-only clubs do not show fake self-join buttons.</li>
              <li>System-managed clubs stay non-claimable.</li>
            </ul>
          </div>
        </div>
      </section>
    );
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading clubs...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <div>
          <h1 className={styles.title}>Discover Clubs</h1>
          <p className={styles.subtitle}>
            Browse listed clubs only. Hidden code-only clubs stay out of search and must be found from the clubs home by code.
          </p>
        </div>

        <div className={styles.heroActions}>
          <button
            className={styles.secondaryButton}
            onClick={() => navigate('/clubs')}
          >
            Back to Clubs
          </button>
        </div>
      </section>

      <section className={styles.searchPanel}>
        <form className={styles.searchForm} onSubmit={handleSearchSubmit}>
          <input
            className={styles.searchInput}
            type="text"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search by club name, city, division, description, or reference club"
          />
          <button className={styles.primaryButton} type="submit">
            Search
          </button>
          {(searchInput || activeSearch) && (
            <button
              className={styles.secondaryButton}
              type="button"
              onClick={handleClearSearch}
            >
              Clear
            </button>
          )}
        </form>

        <div className={styles.searchMeta}>{visibleCountLabel}</div>
      </section>

      {error && <div className={styles.error}>{error}</div>}

      {renderWorkflowPanel()}

      {clubs.length === 0 ? (
        <div className={styles.empty}>
          <p>No listed clubs matched your current search.</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {clubs.map((club) => (
            <ClubCard
              key={club.id}
              club={club}
              variant="browse"
              onCopy={handleCopy}
              onClick={handleSelectClub}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default BrowseClubsPage;