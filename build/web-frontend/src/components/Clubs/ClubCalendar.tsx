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
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function ClubCalendar({ calendarItems, className }: ClubCalendarProps) {
  const today = new Date();

  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const goPrev = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
    setSelectedDay(null);
  };

  const goNext = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
    setSelectedDay(null);
  };

  const { monthName, calendarDays } = useMemo(() => {
    const monthName = new Date(viewYear, viewMonth, 1).toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric',
    });
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const firstDayOfMonth = new Date(viewYear, viewMonth, 1).getDay();

    const calendarDays: (number | null)[][] = [];
    let dayCounter = 1;

    for (let week = 0; week < 6; week++) {
      const weekDays: (number | null)[] = [];
      for (let day = 0; day < 7; day++) {
        if (week === 0 && day < firstDayOfMonth) {
          weekDays.push(null);
        } else if (dayCounter <= daysInMonth) {
          weekDays.push(dayCounter++);
        } else {
          weekDays.push(null);
        }
      }
      calendarDays.push(weekDays);
      if (dayCounter > daysInMonth) break;
    }

    return { monthName, calendarDays };
  }, [viewYear, viewMonth]);

  const getEventsForDay = (day: number): ClubCalendarFeedItem[] => {
    const targetStr = new Date(viewYear, viewMonth, day).toISOString().split('T')[0];
    return calendarItems.filter(
      (item) => new Date(item.sort_datetime).toISOString().split('T')[0] === targetStr
    );
  };

  const handleDayClick = (day: number, events: ClubCalendarFeedItem[]) => {
    if (events.length === 0) return;
    setSelectedDay((prev) => (prev === day ? null : day));
  };

  const isToday = (day: number) =>
    day === today.getDate() &&
    viewMonth === today.getMonth() &&
    viewYear === today.getFullYear();

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const selectedEvents = selectedDay ? getEventsForDay(selectedDay) : [];

  return (
    <div className={`${styles.calendar} ${className || ''}`}>
      <div className={styles.header}>
        <button className={styles.navButton} onClick={goPrev} aria-label="Previous month">
          ‹
        </button>
        <h4 className={styles.title}>{monthName}</h4>
        <button className={styles.navButton} onClick={goNext} aria-label="Next month">
          ›
        </button>
      </div>

      <div className={styles.dayHeaders}>
        {dayNames.map((day) => (
          <div key={day} className={styles.dayHeader}>
            {day}
          </div>
        ))}
      </div>

      <div className={styles.grid}>
        {calendarDays.map((week, weekIndex) => (
          <div key={weekIndex} className={styles.week}>
            {week.map((day, dayIndex) => {
              const events = day ? getEventsForDay(day) : [];
              const hasEvents = events.length > 0;
              const isSelected = day !== null && selectedDay === day;

              return (
                <div
                  key={`${weekIndex}-${dayIndex}`}
                  className={[
                    styles.day,
                    day ? styles.activeDay : styles.emptyDay,
                    isToday(day ?? 0) ? styles.today : '',
                    hasEvents ? styles.hasEvents : '',
                    isSelected ? styles.selectedDay : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
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
                      <div className={styles.dayNumber}>{day}</div>
                      {events.length > 0 && (
                        <div className={styles.events}>
                          {events.slice(0, 2).map((event, i) => (
                            <div
                              key={i}
                              className={`${styles.event} ${
                                event.item_type === 'event' ? styles.eventType : styles.fixtureType
                              }`}
                              title={event.calendar_label}
                            >
                              {event.item_type === 'event' ? 'E' : 'F'}
                            </div>
                          ))}
                          {events.length > 2 && (
                            <div className={styles.moreEvents}>+{events.length - 2}</div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {selectedDay && selectedEvents.length > 0 && (
        <div className={styles.preview}>
          <div className={styles.previewHeader}>
            <span className={styles.previewDate}>
              {new Date(viewYear, viewMonth, selectedDay).toLocaleDateString('en-IE', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
              })}
            </span>
            <button
              className={styles.previewClose}
              onClick={() => setSelectedDay(null)}
              aria-label="Close preview"
            >
              ×
            </button>
          </div>
          <div className={styles.previewItems}>
            {selectedEvents.map((item, i) => {
              const isEvent = item.item_type === 'event';
              const e = item.event;
              const f = item.fixture;
              return (
                <div
                  key={i}
                  className={`${styles.previewItem} ${
                    isEvent ? styles.previewEvent : styles.previewFixture
                  }`}
                >
                  <div className={styles.previewItemTitle}>
                    {isEvent ? e?.title : `vs ${f?.opponent_name}`}
                    <span className={styles.previewItemType}>
                      {isEvent ? e?.event_type_display : f?.fixture_status_display}
                    </span>
                  </div>
                  <div className={styles.previewItemMeta}>
                    {isEvent && e && formatTime(e.start_datetime, e.is_all_day)}
                    {!isEvent && f && formatFullDate(f.match_datetime)}
                  </div>
                  {isEvent && e?.location && (
                    <div className={styles.previewItemDetail}>{e.location}</div>
                  )}
                  {!isEvent && f?.location && (
                    <div className={styles.previewItemDetail}>{f.location}</div>
                  )}
                  {isEvent && e?.description && (
                    <div className={styles.previewItemDetail}>{e.description}</div>
                  )}
                  {isEvent && e?.is_mandatory && (
                    <div className={styles.previewItemMandatory}>Mandatory</div>
                  )}
                  {!isEvent && f?.competition && (
                    <div className={styles.previewItemDetail}>{f.competition}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className={styles.legend}>
        <div className={styles.legendItem}>
          <div className={`${styles.event} ${styles.eventType}`}>E</div>
          <span>Event</span>
        </div>
        <div className={styles.legendItem}>
          <div className={`${styles.event} ${styles.fixtureType}`}>F</div>
          <span>Fixture</span>
        </div>
      </div>
    </div>
  );
}
