import NullStatePlaceholder from '../widgets/NullStatePlaceholder';
import StructuredResponseBlock from './chat/StructuredResponseBlock';
import styles from './css/PinnedOutputsPanel.module.css';

export interface PinnedOutput {
  id: string;
  label: string;
  query_type: string;
  data: unknown;
  pinned_at: string;
  question?: string;
  prose?: string;
}

const MAX_PINNED_OUTPUTS = 4;

interface PinnedOutputsPanelProps {
  pins: PinnedOutput[];
  onDismiss: (id: string) => void;
}

export default function PinnedOutputsPanel({ pins, onDismiss }: PinnedOutputsPanelProps) {
  if (pins.length === 0) {
    return (
      <NullStatePlaceholder
        icon="bookmark"
        message="Pin a response to keep it visible here"
      />
    );
  }

  return (
    <div className={styles.panel}>
      {pins.length === MAX_PINNED_OUTPUTS && (
        <p className={styles.maxNotice}>Max pins reached — dismiss one to add more</p>
      )}
      {[...pins].reverse().map(pin => (
        <div key={pin.id} className={styles.pinCard}>
          <div className={styles.pinHeader}>
            <span className={styles.pinLabel}>{pin.label}</span>
            <span className={styles.pinType}>{pin.query_type}</span>
            <button
              className={styles.dismissBtn}
              onClick={() => onDismiss(pin.id)}
              aria-label={`Dismiss ${pin.label}`}
            >
              ×
            </button>
          </div>
          {pin.question && (
            <p className={styles.pinQuestion}>{pin.question}</p>
          )}
          {pin.prose && (
            <p className={styles.pinProse}>{pin.prose}</p>
          )}
          <StructuredResponseBlock
            queryType={pin.query_type}
            engineData={pin.data as Record<string, unknown>}
            partial={false}
            error={null}
          />
        </div>
      ))}
    </div>
  );
}

export { MAX_PINNED_OUTPUTS };