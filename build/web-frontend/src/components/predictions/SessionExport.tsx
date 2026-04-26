import type { PinnedOutput } from './PinnedOutputsPanel';
import styles from './css/PinnedOutputsPanel.module.css';

interface SessionExportProps {
  pins: PinnedOutput[];
  messages: Array<{ role: string; content: string }>;
  sessionLabel: string;
}

export default function SessionExport({ pins, messages, sessionLabel }: SessionExportProps) {
  const isEmpty = pins.length === 0 && messages.length === 0;

  function handleExport() {
    const data = {
      session_label: sessionLabel,
      exported_at: new Date().toISOString(),
      pinned_outputs: pins,
      conversation_summary: messages.map(m => ({ role: m.role, content: m.content })),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `xggaffer-session-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button
      className={styles.exportBtn}
      onClick={handleExport}
      disabled={isEmpty}
      title={isEmpty ? 'No session data to export' : 'Export session as JSON'}
    >
      Export session
    </button>
  );
}