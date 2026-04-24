import { useState } from 'react';
import ChatInterface from '../../components/predictions/chat/ChatInterface';
import styles from './css/PredictionPage.module.css';

const PREDICTION_STARTER_QUERIES = [
  'Predict Arsenal vs Chelsea this weekend',
  'Compare xgGaffer odds vs bookmaker for Liverpool vs Man City',
  'What lineup will Arsenal use against City?',
  'Which players are at risk of missing the next round?',
  'What are Premier League title probabilities?',
  'Show relegation risk for the bottom six teams',
  'What tactical style does Real Madrid use?',
  'What is xG?',
  'Explain how xgGaffer uses Dixon-Coles',
] as const;

const SESSION_LABEL = 'xgGaffer Analytics';
const PINNED_EMPTY_MESSAGE = 'Pin a response to keep it visible here';

function clearSession() {}

export default function PredictionPage() {
  const [showPinned, setShowPinned] = useState(false);

  return (
    <div className={styles.predictionPageRoot}>
      <div className={styles.predictionToolbar}>
        <span className={styles.predictionToolbarLeft}>{SESSION_LABEL}</span>
        <div className={styles.predictionToolbarRight}>
          <button
            className={`${styles.predictionToolbarBtn} ${styles.predictionToolbarBtnDisabled}`}
            disabled
            title="Export coming soon"
          >
            Export
          </button>
          <button
            className={styles.predictionToolbarBtn}
            onClick={clearSession}
          >
            Clear session
          </button>
          <button
            className={styles.predictionToolbarBtn}
            onClick={() => setShowPinned((v) => !v)}
          >
            Pinned (0)
          </button>
        </div>
      </div>

      <div className={styles.predictionBody}>
        <div className={styles.predictionChatPanel}>
          <ChatInterface starterQueries={PREDICTION_STARTER_QUERIES} />
        </div>

        <div
          className={`${styles.predictionPinnedPanel} ${showPinned ? styles.predictionPinnedPanelVisible : ''}`}
        >
          {showPinned && (
            <button
              className={styles.predictionPinnedBack}
              onClick={() => setShowPinned(false)}
            >
              ← Back to chat
            </button>
          )}
          <div className={styles.predictionPinnedEmpty}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>
            <span>{PINNED_EMPTY_MESSAGE}</span>
          </div>
        </div>
      </div>
    </div>
  );
}