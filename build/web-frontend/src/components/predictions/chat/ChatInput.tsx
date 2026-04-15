import { useState } from 'react';

import styles from './css/ChatInput.module.css';

const MAX_QUERY_LENGTH = 500;

interface ChatInputProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSubmit, isLoading }: ChatInputProps) {
  const [inputValue, setInputValue] = useState('');

  const canSubmit =
    !isLoading &&
    inputValue.trim().length > 0 &&
    inputValue.length <= MAX_QUERY_LENGTH;

  function handleSubmit() {
    if (!canSubmit) return;
    onSubmit(inputValue.trim());
    setInputValue('');
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit();
    }
  }

  const isOverLimit = inputValue.length > MAX_QUERY_LENGTH;

  return (
    <div className={styles.container}>
      <div className={styles.inputRow}>
        <input
          className={styles.input}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="Ask anything about football analytics..."
          aria-label="Query input"
        />
        <button
          className={styles.button}
          onClick={handleSubmit}
          disabled={!canSubmit}
          aria-label="Send query"
        >
          {isLoading ? '...' : 'Send'}
        </button>
      </div>
      {inputValue.length > 0 && (
        <span className={`${styles.charCount} ${isOverLimit ? styles.charCountError : ''}`}>
          {inputValue.length} / {MAX_QUERY_LENGTH}
        </span>
      )}
    </div>
  );
}