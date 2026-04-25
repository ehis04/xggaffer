import { useState } from 'react';
import ChatInterface from '../../components/predictions/chat/ChatInterface';
import PinnedOutputsPanel, { MAX_PINNED_OUTPUTS } from '../../components/predictions/PinnedOutputsPanel';
import type { PinnedOutput } from '../../components/predictions/PinnedOutputsPanel';
import FileAttachment from '../../components/predictions/FileAttachment';
import type { FileAttachmentData } from '../../components/predictions/FileAttachment';
import SessionExport from '../../components/predictions/SessionExport';
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

export default function PredictionPage() {
  const [pins, setPins] = useState<PinnedOutput[]>([]);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [showPinned, setShowPinned] = useState(false);
  const [attachment, setAttachment] = useState<FileAttachmentData | null>(null);
  const [clearTrigger, setClearTrigger] = useState(0);

  function handlePin(output: PinnedOutput) {
    setPins(prev => [output, ...prev].slice(0, MAX_PINNED_OUTPUTS));
  }

  function handleClearSession() {
    setPins([]);
    setMessages([]);
    setAttachment(null);
    setClearTrigger(n => n + 1);
  }

  return (
    <div className={styles.predictionPageRoot}>
      <div className={styles.predictionToolbar}>
        <span className={styles.predictionToolbarLeft}>{SESSION_LABEL}</span>
        <div className={styles.predictionToolbarRight}>
          <SessionExport pins={pins} messages={messages} sessionLabel={SESSION_LABEL} />
          <button className={styles.predictionToolbarBtn} onClick={handleClearSession}>
            Clear session
          </button>
          <button
            className={styles.predictionToolbarBtn}
            onClick={() => setShowPinned(v => !v)}
          >
            Pinned ({pins.length})
          </button>
        </div>
      </div>

      <div className={styles.predictionBody}>
        <div className={styles.predictionChatPanel}>
          <ChatInterface
            key={clearTrigger}
            starterQueries={PREDICTION_STARTER_QUERIES}
            onMessagesChange={setMessages}
            onPin={handlePin}
            attachment={attachment}
            onAttachmentUsed={() => setAttachment(null)}
          />
          <div className={styles.attachmentRow}>
            <FileAttachment
              current={attachment}
              onAttach={setAttachment}
              onClear={() => setAttachment(null)}
            />
          </div>
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
          <PinnedOutputsPanel
            pins={pins}
            onDismiss={id => setPins(prev => prev.filter(p => p.id !== id))}
          />
        </div>
      </div>
    </div>
  );
}