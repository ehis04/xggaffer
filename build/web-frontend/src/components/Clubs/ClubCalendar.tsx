import { useMemo, useState } from 'react';
import type { ClubCalendarFeedItem } from '../../types/club';
import styles from './css/ClubCalendar.module.css';

interface ClubCalendarProps {
  calendarItems: ClubCalendarFeedItem[];
  className?: string;
}

function formatTime(dateStr: string, isAllDay: boolean): string {
  if (isAllDay) return 'All day';
  return new Date(dateStr).toLocaleTimeString('en-IE', { hour: '2-digit', minute: '2-digit' });
}

function formatFullDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IE', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  });
}

export function ClubCalendar({ calendarItems, className }: ClubCalendarProps) {
  const today = new Date();

  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const goPrev = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1); }
    else setViewMonth((m) => m - 1);
    setSelectedDay(null);
  };

  const goNext = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1); }
    else setViewMonth((m) => m + 1);
    setSelectedDay(null);
  };

  const { monthName, calendarDays } = useMemo(() => {
    const monthName = new Date(viewYear, viewMonth, 1).toLocaleDateString('en-US', {
      month: 'long', year: 'numeric',
    });
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const firstDayOfMonth = new Date(viewYear, viewMonth, 1).getDay();

    const calendarDays: (number | null)[][] = [];
    let dayCounter = 1;
    for (let week = 0; week < 6; week++) {
      const weekDays: (number | null)[] = [];
      for (let day = 0; day < 7; day++) {
        if (week === 0 && day < firstDayOfMonth) weekDays.push(null);
        else if (dayCounter <= daysInMonth) weekDays.push(dayCounter++);
        else weekDays.push(null);
      }
      calendarDays.push(weekDays);
      if (dayCounter > daysInMonth) break;
    }
    return { monthName, calendarDays };
  }, [viewYear, viewMonth]);

  const getEventsForDay = (day: number): ClubCalendarFeedItem[] => {
    // Use local date string to avoid UTC conversion issues
    const targetDate = new Date(viewYear, viewMonth, day);
    const targetStr = `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, '0')}-${String(targetDate.getDate()).padStart(2, '0')}`;
    return calendarItems.filter(
      (item) => item.sort_datetime.split('T')[0] === targetStr
    );
  };

  const handleDayClick = (day: number, events: ClubCalendarFeedItem[]) => {
    if (events.length === 0) return;
    setSelectedDay((prev) => (prev === day ? null : day));
  };

  const isToday = (day: number) =>
    day === today.getDate() && viewMonth === today.getMonth() && viewYear === today.getFullYear();

  const dayNames = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
  const selectedEvents = selectedDay ? getEventsForDay(selectedDay) : [];

  return (
    <div className={`${styles.clubCalendarRoot} ${className ?? ''}`}>

      <div className={styles.clubCalendarHeader}>
        <h4 className={styles.clubCalendarMonth}>{monthName}</h4>
        <div className={styles.clubCalendarNavBtns}>
          <button className={styles.clubCalendarNavBtn} onClick={goPrev} aria-label="Previous month">‹</button>
          <button className={styles.clubCalendarNavBtn} onClick={goNext} aria-label="Next month">›</button>
        </div>
      </div>

      <div className={styles.clubCalendarDayHeaders}>
        {dayNames.map((d, i) => (
          <div key={i} className={styles.clubCalendarDayHeader}>{d}</div>
        ))}
      </div>

      <div className={styles.clubCalendarGrid}>
        {calendarDays.map((week, wi) =>
          week.map((day, di) => {
            const events = day ? getEventsForDay(day) : [];
            const hasEvents = events.length > 0;
            const isSelected = day !== null && selectedDay === day;
            const todayDay = day !== null && isToday(day);

            const hasTraining = events.some((e) => e.item_type === 'event');
            const hasFixture = events.some((e) => e.item_type === 'fixture');

            return (
              <div
                key={`${wi}-${di}`}
                className={[
                  styles.clubCalendarCell,
                  !day ? styles.clubCalendarCellEmpty : '',
                  todayDay ? styles.clubCalendarCellToday : '',
                  isSelected ? styles.clubCalendarCellSelected : '',
                  hasEvents && !isSelected ? styles.clubCalendarCellHasEvents : '',
                ].filter(Boolean).join(' ')}
                onClick={() => day && handleDayClick(day, events)}
                role={hasEvents ? 'button' : undefined}
                tabIndex={hasEvents ? 0 : undefined}
                onKeyDown={(e) => {
                  if (day && hasEvents && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault();
                    handleDayClick(day, events);
                  }
                }}
              >
                {day && (
                  <>
                    <span className={styles.clubCalendarCellNum}>{day}</span>
                    {hasEvents && (
                      <div className={styles.clubCalendarDots}>
                        {hasTraining && <span className={styles.clubCalendarDotTraining} />}
                        {hasFixture && <span className={styles.clubCalendarDotFixture} />}
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })
        )}
      </div>

      {selectedDay && selectedEvents.length > 0 && (
        <div className={styles.clubCalendarPreview}>
          <div className={styles.clubCalendarPreviewHead}>
            <span className={styles.clubCalendarPreviewDate}>
              {new Date(viewYear, viewMonth, selectedDay).toLocaleDateString('en-IE', {
                weekday: 'long', day: 'numeric', month: 'long',
              })}
            </span>
            <button
              className={styles.clubCalendarPreviewClose}
              onClick={() => setSelectedDay(null)}
              aria-label="Close preview"
            >
              ×
            </button>
          </div>
          <div className={styles.clubCalendarPreviewItems}>
            {selectedEvents.map((item, i) => {
              const isEvent = item.item_type === 'event';
              const e = item.event;
              const f = item.fixture;
              return (
                <div
                  key={i}
                  className={`${styles.clubCalendarPreviewItem} ${isEvent ? styles.clubCalendarPreviewItemEvent : styles.clubCalendarPreviewItemFixture}`}
                >
                  <div className={styles.clubCalendarPreviewItemTop}>
                    <span className={styles.clubCalendarPreviewItemTitle}>
                      {isEvent ? e?.title : `vs ${f?.opponent_name}`}
                    </span>
                    <span className={styles.clubCalendarPreviewItemBadge}>
                      {isEvent ? e?.event_type_display : f?.fixture_status_display}
                    </span>
                  </div>
                  <div className={styles.clubCalendarPreviewItemMeta}>
                    {isEvent && e && formatTime(e.start_datetime, e.is_all_day)}
                    {!isEvent && f && formatFullDate(f.match_datetime)}
                  </div>
                  {isEvent && e?.location && (
                    <div className={styles.clubCalendarPreviewItemDetail}>{e.location}</div>
                  )}
                  {!isEvent && f?.location && (
                    <div className={styles.clubCalendarPreviewItemDetail}>{f.location}</div>
                  )}
                  {isEvent && e?.description && (
                    <div className={styles.clubCalendarPreviewItemDetail}>{e.description}</div>
                  )}
                  {isEvent && e?.is_mandatory && (
                    <span className={styles.clubCalendarPreviewItemMandatory}>Mandatory</span>
                  )}
                  {!isEvent && f?.competition && (
                    <div className={styles.clubCalendarPreviewItemDetail}>{f.competition}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className={styles.clubCalendarLegend}>
        <div className={styles.clubCalendarLegendItem}>
          <span className={styles.clubCalendarDotTraining} />
          <span className={styles.clubCalendarLegendLabel}>Training</span>
        </div>
        <div className={styles.clubCalendarLegendItem}>
          <span className={styles.clubCalendarDotFixture} />
          <span className={styles.clubCalendarLegendLabel}>Fixture</span>
        </div>
      </div>
    </div>
  );
}