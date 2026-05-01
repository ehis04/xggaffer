import { useCallback, useEffect, useState } from 'react';
import { clubsApi } from '../../../../services/api';
import { ClubCalendar } from '../../../../components/Clubs';
import ClubResourcesSection from '../../clubs/resources/ClubResourcesSection';
import type { ClubContext } from '../IndividualClubBase';
import type {
  ClubEvent,
  ClubCalendarFeedItem,
  Fixture,
  ClubEventType,
  FixtureVenue,
  FixtureStatus,
  CreateClubEventPayload,
  CreateFixturePayload,
} from '../../../../types/club';
import styles from './css/ScheduleTab.module.css';
import { SectionSkeleton } from '../../../../common/components/SectionSkeleton';
import { InlineRetry } from '../../../../common/components/InlineRetry';

interface Props {
  ctx: ClubContext;
}

type SubView = 'calendar' | 'events' | 'fixtures' | 'files';

const EVENT_TYPE_OPTIONS: { value: ClubEventType; label: string }[] = [
  { value: 'training', label: 'Training' },
  { value: 'meeting', label: 'Meeting' },
  { value: 'social', label: 'Social' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'other', label: 'Other' },
];

const FIXTURE_VENUE_OPTIONS: { value: FixtureVenue; label: string }[] = [
  { value: 'home', label: 'Home' },
  { value: 'away', label: 'Away' },
  { value: 'neutral', label: 'Neutral' },
];

const FIXTURE_STATUS_OPTIONS: { value: FixtureStatus; label: string }[] = [
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'completed', label: 'Completed' },
  { value: 'postponed', label: 'Postponed' },
  { value: 'cancelled', label: 'Cancelled' },
];

interface EventFormState {
  title: string;
  event_type: ClubEventType;
  description: string;
  start_datetime: string;
  end_datetime: string;
  is_all_day: boolean;
  location: string;
  is_mandatory: boolean;
}

interface FixtureFormState {
  opponent_name: string;
  venue: FixtureVenue;
  competition: string;
  match_datetime: string;
  location: string;
  fixture_status: FixtureStatus;
}

const emptyEventForm = (): EventFormState => ({
  title: '', event_type: 'training', description: '',
  start_datetime: '', end_datetime: '',
  is_all_day: false, location: '', is_mandatory: false,
});

const emptyFixtureForm = (): FixtureFormState => ({
  opponent_name: '', venue: 'home', competition: '',
  match_datetime: '', location: '', fixture_status: 'scheduled',
});

const fmtDT = (v: string): string =>
  new Date(v).toLocaleString('en-IE', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });

const toLocalValue = (v: string | null): string => {
  if (!v) return '';
  const d = new Date(v);
  const offset = d.getTimezoneOffset() * 60_000;
  return new Date(d.getTime() - offset).toISOString().slice(0, 16);
};

const ScheduleTab = ({ ctx }: Props) => {
  const { club, clubId, canManage, isMember } = ctx;
  const isProClub = club.club_type === 'system_professional';

  const [subView, setSubView] = useState<SubView>('calendar');
  const [calendarFeed, setCalendarFeed] = useState<ClubCalendarFeedItem[]>([]);
  const [events, setEvents] = useState<ClubEvent[]>([]);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const [editingEventId, setEditingEventId] = useState<number | null>(null);
  const [eventForm, setEventForm] = useState<EventFormState>(emptyEventForm());
  const [eventError, setEventError] = useState<string | null>(null);

  const [editingFixtureId, setEditingFixtureId] = useState<number | null>(null);
  const [fixtureForm, setFixtureForm] = useState<FixtureFormState>(emptyFixtureForm());
  const [fixtureError, setFixtureError] = useState<string | null>(null);

  const canSchedule = canManage && !isProClub;

  const loadScheduling = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [feed, evData, fxData] = await Promise.all([
        clubsApi.listCalendarFeed(clubId, { limit: 100 }),
        clubsApi.listEvents(clubId),
        clubsApi.listFixtures(clubId),
      ]);
      setCalendarFeed(feed);
      setEvents(evData);
      setFixtures(fxData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scheduling data.');
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => { void loadScheduling(); }, [loadScheduling]);

  // ── Event handlers ──────────────────────────────────────────────────────────

  const handleEventSubmit = async () => {
    if (!eventForm.title.trim()) { setEventError('Title is required.'); return; }
    if (!eventForm.start_datetime) { setEventError('Start date/time is required.'); return; }
    try {
      const key = editingEventId !== null ? `save-event-${editingEventId}` : 'create-event';
      setLoadingKey(key);
      setEventError(null);
      const payload: CreateClubEventPayload = {
        title: eventForm.title.trim(),
        event_type: eventForm.event_type,
        description: eventForm.description.trim(),
        start_datetime: new Date(eventForm.start_datetime).toISOString(),
        end_datetime: eventForm.end_datetime
          ? new Date(eventForm.end_datetime).toISOString() : null,
        is_all_day: eventForm.is_all_day,
        location: eventForm.location.trim(),
        is_mandatory: eventForm.is_mandatory,
      };
      if (editingEventId !== null) {
        await clubsApi.updateEvent(clubId, editingEventId, payload);
      } else {
        await clubsApi.createEvent(clubId, payload);
      }
      setEventForm(emptyEventForm());
      setEditingEventId(null);
      await loadScheduling();
    } catch (err) {
      setEventError(err instanceof Error ? err.message : 'Failed to save event.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleEditEvent = (ev: ClubEvent) => {
    setEditingEventId(ev.id);
    setEventForm({
      title: ev.title,
      event_type: ev.event_type,
      description: ev.description,
      start_datetime: toLocalValue(ev.start_datetime),
      end_datetime: toLocalValue(ev.end_datetime),
      is_all_day: ev.is_all_day,
      location: ev.location,
      is_mandatory: ev.is_mandatory,
    });
    setEventError(null);
    setSubView('events');
  };

  const handleDeleteEvent = async (ev: ClubEvent) => {
    if (!window.confirm(`Delete "${ev.title}"?`)) return;
    try {
      setLoadingKey(`delete-event-${ev.id}`);
      await clubsApi.deleteEvent(clubId, ev.id);
      await loadScheduling();
    } catch (err) {
      setEventError(err instanceof Error ? err.message : 'Failed to delete event.');
    } finally {
      setLoadingKey(null);
    }
  };

  // ── Fixture handlers ─────────────────────────────────────────────────────────

  const handleFixtureSubmit = async () => {
    if (!fixtureForm.opponent_name.trim()) { setFixtureError('Opponent is required.'); return; }
    if (!fixtureForm.match_datetime) { setFixtureError('Match date/time is required.'); return; }
    try {
      const key = editingFixtureId !== null ? `save-fixture-${editingFixtureId}` : 'create-fixture';
      setLoadingKey(key);
      setFixtureError(null);
      const payload: CreateFixturePayload = {
        opponent_name: fixtureForm.opponent_name.trim(),
        venue: fixtureForm.venue,
        competition: fixtureForm.competition.trim(),
        match_datetime: new Date(fixtureForm.match_datetime).toISOString(),
        location: fixtureForm.location.trim(),
        fixture_status: fixtureForm.fixture_status,
      };
      if (editingFixtureId !== null) {
        await clubsApi.updateFixture(clubId, editingFixtureId, payload);
      } else {
        await clubsApi.createFixture(clubId, payload);
      }
      setFixtureForm(emptyFixtureForm());
      setEditingFixtureId(null);
      await loadScheduling();
    } catch (err) {
      setFixtureError(err instanceof Error ? err.message : 'Failed to save fixture.');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleEditFixture = (fx: Fixture) => {
    setEditingFixtureId(fx.id);
    setFixtureForm({
      opponent_name: fx.opponent_name,
      venue: fx.venue,
      competition: fx.competition,
      match_datetime: toLocalValue(fx.match_datetime),
      location: fx.location,
      fixture_status: fx.fixture_status,
    });
    setFixtureError(null);
    setSubView('fixtures');
  };

  const handleDeleteFixture = async (fx: Fixture) => {
    if (!window.confirm(`Delete fixture vs ${fx.opponent_name}?`)) return;
    try {
      setLoadingKey(`delete-fixture-${fx.id}`);
      await clubsApi.deleteFixture(clubId, fx.id);
      await loadScheduling();
    } catch (err) {
      setFixtureError(err instanceof Error ? err.message : 'Failed to delete fixture.');
    } finally {
      setLoadingKey(null);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  const SUB_TABS: { value: SubView; label: string }[] = [
    { value: 'calendar', label: 'Calendar' },
    { value: 'events', label: 'Events' },
    { value: 'fixtures', label: 'Fixtures' },
    { value: 'files', label: 'Files' },
  ];

  return (
    <div className={styles.tabContent}>
      <div className={styles.topBar}>
        <div className={styles.subViewTabs}>
          {SUB_TABS.map((t) => (
            <button
              key={t.value}
              type="button"
              className={`${styles.subTab}${subView === t.value ? ' ' + styles.subTabActive : ''}`}
              onClick={() => setSubView(t.value)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <SectionSkeleton rows={3} height="56px" gap="12px" />}
      {error && (
        <InlineRetry
          message={error}
          onRetry={loadScheduling}
          retrying={loading}
        />
      )}

      {!loading && !error && (
        <>
          {/* ── Calendar ─────────────────────────────────────────────────── */}
          {subView === 'calendar' && (
            <div className={styles.calendarSection}>
              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <span className={styles.sectionLabel}>Upcoming</span>
                  <span className={styles.badge}>{calendarFeed.length} items</span>
                </div>
                {calendarFeed.length === 0 ? (
                  <p className={styles.emptyText}>No upcoming events or fixtures scheduled.</p>
                ) : (
                  <div className={styles.feedList}>
                    {calendarFeed.map((item) => {
                      const id = item.item_type === 'event' ? item.event?.id : item.fixture?.id;
                      return (
                        <div key={`${item.item_type}-${id}`} className={styles.feedItem}>
                          <div className={styles.feedItemLeft}>
                            <span className={`${styles.itemTypeBadge} ${item.item_type === 'fixture' ? styles.fixtureBadge : styles.eventBadge}`}>
                              {item.item_type === 'event' ? 'Event' : 'Fixture'}
                            </span>
                            <div>
                              <span className={styles.feedItemTitle}>{item.calendar_label}</span>
                              <span className={styles.feedItemMeta}>{fmtDT(item.sort_datetime)}</span>
                              {item.item_type === 'event' && item.event?.location && (
                                <span className={styles.feedItemMeta}>{item.event.location}</span>
                              )}
                              {item.item_type === 'fixture' && item.fixture?.location && (
                                <span className={styles.feedItemMeta}>{item.fixture.location}</span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <span className={styles.sectionLabel}>Calendar view</span>
                </div>
                <ClubCalendar calendarItems={calendarFeed} />
              </div>
            </div>
          )}

          {/* ── Events ───────────────────────────────────────────────────── */}
          {subView === 'events' && (
            <div className={styles.twoCol}>
              {canSchedule && (
                <div className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelTitle}>
                      {editingEventId !== null ? 'Edit event' : 'Add event'}
                    </span>
                    {editingEventId !== null && (
                      <button type="button" className={styles.ghostBtn}
                        onClick={() => { setEditingEventId(null); setEventForm(emptyEventForm()); }}>
                        Cancel
                      </button>
                    )}
                  </div>

                  {eventError && <div className={styles.errorNotice}>{eventError}</div>}

                  <div className={styles.formGrid}>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="ev_title">Title</label>
                      <input id="ev_title" className={styles.input}
                        value={eventForm.title}
                        onChange={(e) => setEventForm((p) => ({ ...p, title: e.target.value }))}
                        placeholder="e.g. Tuesday training" />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="ev_type">Type</label>
                      <select id="ev_type" className={styles.select}
                        value={eventForm.event_type}
                        onChange={(e) => setEventForm((p) => ({ ...p, event_type: e.target.value as ClubEventType }))}>
                        {EVENT_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="ev_start">Start</label>
                      <input id="ev_start" type="datetime-local" className={styles.input}
                        value={eventForm.start_datetime}
                        onChange={(e) => setEventForm((p) => ({ ...p, start_datetime: e.target.value }))} />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="ev_end">End</label>
                      <input id="ev_end" type="datetime-local" className={styles.input}
                        value={eventForm.end_datetime}
                        onChange={(e) => setEventForm((p) => ({ ...p, end_datetime: e.target.value }))} />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="ev_location">Location</label>
                      <input id="ev_location" className={styles.input}
                        value={eventForm.location}
                        onChange={(e) => setEventForm((p) => ({ ...p, location: e.target.value }))}
                        placeholder="e.g. Main pitch" />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="ev_desc">Description</label>
                      <textarea id="ev_desc" className={styles.textarea} rows={2}
                        value={eventForm.description}
                        onChange={(e) => setEventForm((p) => ({ ...p, description: e.target.value }))}
                        placeholder="Optional details" />
                    </div>
                    <div className={styles.checkboxRow}>
                      <label className={styles.checkboxLabel}>
                        <input type="checkbox" checked={eventForm.is_all_day}
                          onChange={(e) => setEventForm((p) => ({ ...p, is_all_day: e.target.checked }))} />
                        All day
                      </label>
                      <label className={styles.checkboxLabel}>
                        <input type="checkbox" checked={eventForm.is_mandatory}
                          onChange={(e) => setEventForm((p) => ({ ...p, is_mandatory: e.target.checked }))} />
                        Mandatory
                      </label>
                    </div>
                  </div>

                  <div className={styles.formActions}>
                    <button type="button" className={styles.primaryBtn}
                      disabled={loadingKey === 'create-event' || loadingKey === `save-event-${editingEventId}`}
                      onClick={handleEventSubmit}>
                      {editingEventId !== null
                        ? (loadingKey === `save-event-${editingEventId}` ? 'Saving...' : 'Save event')
                        : (loadingKey === 'create-event' ? 'Creating...' : 'Create event')}
                    </button>
                  </div>
                </div>
              )}

              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <span className={styles.panelTitle}>Club events</span>
                  <span className={styles.badge}>{events.length}</span>
                </div>
                {events.length === 0 ? (
                  <p className={styles.emptyText}>No events scheduled yet.</p>
                ) : (
                  <div className={styles.itemList}>
                    {events.map((ev) => (
                      <div key={ev.id} className={styles.listItem}>
                        <div className={styles.listItemHeader}>
                          <div>
                            <span className={styles.listItemTitle}>{ev.title}</span>
                            <span className={styles.listItemMeta}>
                              {ev.event_type_display} · {fmtDT(ev.start_datetime)}
                            </span>
                            {ev.location && <span className={styles.listItemMeta}>{ev.location}</span>}
                            {ev.description && <span className={styles.listItemMeta}>{ev.description}</span>}
                            {ev.is_mandatory && <span className={styles.mandatoryBadge}>Mandatory</span>}
                          </div>
                          <span className={styles.sourceBadge}>{ev.source_type_display}</span>
                        </div>
                        {canSchedule && ev.is_user_editable && (
                          <div className={styles.itemActions}>
                            <button type="button" className={styles.ghostBtn}
                              onClick={() => handleEditEvent(ev)}>Edit</button>
                            <button type="button" className={styles.dangerBtn}
                              disabled={loadingKey === `delete-event-${ev.id}`}
                              onClick={() => handleDeleteEvent(ev)}>
                              {loadingKey === `delete-event-${ev.id}` ? 'Deleting...' : 'Delete'}
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Fixtures ─────────────────────────────────────────────────── */}
          {subView === 'fixtures' && (
            <div className={styles.twoCol}>
              {canSchedule && (
                <div className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelTitle}>
                      {editingFixtureId !== null ? 'Edit fixture' : 'Add fixture'}
                    </span>
                    {editingFixtureId !== null && (
                      <button type="button" className={styles.ghostBtn}
                        onClick={() => { setEditingFixtureId(null); setFixtureForm(emptyFixtureForm()); }}>
                        Cancel
                      </button>
                    )}
                  </div>

                  {fixtureError && <div className={styles.errorNotice}>{fixtureError}</div>}

                  <div className={styles.formGrid}>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="fx_opponent">Opponent</label>
                      <input id="fx_opponent" className={styles.input}
                        value={fixtureForm.opponent_name}
                        onChange={(e) => setFixtureForm((p) => ({ ...p, opponent_name: e.target.value }))}
                        placeholder="e.g. Dublin City FC" />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="fx_venue">Venue</label>
                      <select id="fx_venue" className={styles.select}
                        value={fixtureForm.venue}
                        onChange={(e) => setFixtureForm((p) => ({ ...p, venue: e.target.value as FixtureVenue }))}>
                        {FIXTURE_VENUE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="fx_comp">Competition</label>
                      <input id="fx_comp" className={styles.input}
                        value={fixtureForm.competition}
                        onChange={(e) => setFixtureForm((p) => ({ ...p, competition: e.target.value }))}
                        placeholder="e.g. League" />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="fx_status">Status</label>
                      <select id="fx_status" className={styles.select}
                        value={fixtureForm.fixture_status}
                        onChange={(e) => setFixtureForm((p) => ({ ...p, fixture_status: e.target.value as FixtureStatus }))}>
                        {FIXTURE_STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="fx_dt">Match date/time</label>
                      <input id="fx_dt" type="datetime-local" className={styles.input}
                        value={fixtureForm.match_datetime}
                        onChange={(e) => setFixtureForm((p) => ({ ...p, match_datetime: e.target.value }))} />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.label} htmlFor="fx_location">Location</label>
                      <input id="fx_location" className={styles.input}
                        value={fixtureForm.location}
                        onChange={(e) => setFixtureForm((p) => ({ ...p, location: e.target.value }))}
                        placeholder="e.g. Home ground" />
                    </div>
                  </div>

                  <div className={styles.formActions}>
                    <button type="button" className={styles.primaryBtn}
                      disabled={loadingKey === 'create-fixture' || loadingKey === `save-fixture-${editingFixtureId}`}
                      onClick={handleFixtureSubmit}>
                      {editingFixtureId !== null
                        ? (loadingKey === `save-fixture-${editingFixtureId}` ? 'Saving...' : 'Save fixture')
                        : (loadingKey === 'create-fixture' ? 'Creating...' : 'Create fixture')}
                    </button>
                  </div>
                </div>
              )}

              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <span className={styles.panelTitle}>Fixtures</span>
                  <span className={styles.badge}>{fixtures.length}</span>
                </div>
                {fixtures.length === 0 ? (
                  <p className={styles.emptyText}>No fixtures scheduled yet.</p>
                ) : (
                  <div className={styles.itemList}>
                    {fixtures.map((fx) => (
                      <div key={fx.id} className={styles.listItem}>
                        <div className={styles.listItemHeader}>
                          <div>
                            <span className={styles.listItemTitle}>{fx.calendar_label}</span>
                            <span className={styles.listItemMeta}>
                              {fx.competition || 'Fixture'} · {fmtDT(fx.match_datetime)}
                            </span>
                            <span className={styles.listItemMeta}>
                              {fx.venue_display} · {fx.fixture_status_display}
                            </span>
                            {fx.location && <span className={styles.listItemMeta}>{fx.location}</span>}
                          </div>
                          <span className={styles.sourceBadge}>{fx.source_type_display}</span>
                        </div>
                        {canSchedule && fx.is_user_editable && (
                          <div className={styles.itemActions}>
                            <button type="button" className={styles.ghostBtn}
                              onClick={() => handleEditFixture(fx)}>Edit</button>
                            <button type="button" className={styles.dangerBtn}
                              disabled={loadingKey === `delete-fixture-${fx.id}`}
                              onClick={() => handleDeleteFixture(fx)}>
                              {loadingKey === `delete-fixture-${fx.id}` ? 'Deleting...' : 'Delete'}
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Files ────────────────────────────────────────────────────── */}
          {subView === 'files' && (
            <ClubResourcesSection
              club={club}
              isMember={isMember}
              canManageResources={canManage}
            />
          )}
        </>
      )}
    </div>
  );
};

export default ScheduleTab;