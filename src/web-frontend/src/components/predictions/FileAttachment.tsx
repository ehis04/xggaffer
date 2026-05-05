import { useRef, useState } from 'react';
import styles from './css/FileAttachment.module.css';

export interface FileAttachmentData {
  type: 'image' | 'csv' | 'text';
  filename: string;
  content: string;
  media_type: string;
  context_text: string;
}

const MAX_ATTACHMENT_SIZE_MB = 5;
const MAX_ATTACHMENT_SIZE_BYTES = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024;
const UPLOAD_TEXT_MAX_CHARS = 4000;
const CSV_CONTEXT_MAX_ROWS = 5;
const SUPPORTED_MIME_TYPES = ['image/jpeg', 'image/png', 'text/plain', 'text/csv'];

interface FileAttachmentProps {
  onAttach: (attachment: FileAttachmentData) => void;
  onClear: () => void;
  current: FileAttachmentData | null;
}

function readAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('File read failed'));
    reader.readAsDataURL(file);
  });
}

function readAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('File read failed'));
    reader.readAsText(file);
  });
}

function formatCsv(filename: string, raw: string): string {
  const lines = raw.split('\n').filter(l => l.trim());
  const headers = lines[0] ?? '';
  const dataRows = lines.slice(1, CSV_CONTEXT_MAX_ROWS + 1);
  const totalRows = lines.length - 1;
  const columns = headers.split(',').map(h => h.trim()).join(', ');
  const sample = dataRows.map(r => r.split(',').join('\t')).join('\n');
  return `[Attached CSV: ${filename} — ${totalRows} rows]\nColumns: ${columns}\nSample:\n${sample}`;
}

export default function FileAttachment({ onAttach, onClear, current }: FileAttachmentProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!inputRef.current) return;
    inputRef.current.value = '';
    if (!file) return;
    setError(null);

    if (!SUPPORTED_MIME_TYPES.includes(file.type)) {
      setError(`Unsupported file type. Allowed: ${SUPPORTED_MIME_TYPES.join(', ')}`);
      return;
    }
    if (file.size > MAX_ATTACHMENT_SIZE_BYTES) {
      setError(`File too large. Max ${MAX_ATTACHMENT_SIZE_MB}MB.`);
      return;
    }

    if (file.type === 'image/jpeg' || file.type === 'image/png') {
      const dataUrl = await readAsDataURL(file);
      const base64 = dataUrl.split(',')[1];
      onAttach({
        type: 'image',
        filename: file.name,
        content: base64,
        media_type: file.type,
        context_text: `[Image attached: ${file.name}]`,
      });
      return;
    }

    const text = await readAsText(file);

    if (file.type === 'text/plain') {
      const truncated = text.slice(0, UPLOAD_TEXT_MAX_CHARS);
      onAttach({
        type: 'text',
        filename: file.name,
        content: truncated,
        media_type: 'text/plain',
        context_text: truncated,
      });
      return;
    }

    if (file.type === 'text/csv') {
      const contextText = formatCsv(file.name, text);
      onAttach({
        type: 'csv',
        filename: file.name,
        content: contextText,
        media_type: 'text/csv',
        context_text: contextText,
      });
    }
  }

  return (
    <div className={styles.wrapper}>
      <input
        ref={inputRef}
        type="file"
        className={styles.hiddenInput}
        accept="image/jpeg,image/png,text/plain,text/csv"
        onChange={handleChange}
        aria-label="Attach file"
      />
      {current ? (
        <span className={styles.chip}>
          <span className={styles.filename}>{current.filename}</span>
          <button
            className={styles.clearBtn}
            onClick={onClear}
            aria-label="Remove attachment"
          >
            ×
          </button>
        </span>
      ) : (
        <button
          className={styles.paperclipBtn}
          onClick={() => inputRef.current?.click()}
          aria-label="Attach file"
          title="Attach file"
          type="button"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.41 17.41a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
        </button>
      )}
      {error && <p className={styles.errorText}>{error}</p>}
    </div>
  );
}