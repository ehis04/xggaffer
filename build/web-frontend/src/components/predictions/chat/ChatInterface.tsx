import { useEffect, useRef, useState } from 'react';

import { chatQuery } from '../../../services/api/predictionsApi';
import type { ChatResponse } from '../../../types/prediction';
import ChatInput from './ChatInput';
import StructuredResponseBlock from './StructuredResponseBlock';
import styles from './css/ChatInterface.module.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
}

const STARTER_QUERIES = [
  'Who wins Arsenal vs Chelsea?',
  'What is xG?',
  'Who wins the Premier League this season?',
  'What lineup will Arsenal use?',
] as const;

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [inputError, setInputError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages.length, isLoading]);

  async function handleSubmit(query: string) {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setInputError(null);

    try {
      const response = await chatQuery(query);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.prose,
        response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setInputError('Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.messageList} ref={listRef}>
        {messages.length === 0 && (
          <div className={styles.starterChips}>
            {STARTER_QUERIES.map((q) => (
              <button
                key={q}
                className={styles.chip}
                onClick={() => handleSubmit(q)}
                disabled={isLoading}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={msg.role === 'user' ? styles.userMessage : styles.assistantMessage}
          >
            <p className={styles.messageText}>{msg.content}</p>
            {msg.role === 'assistant' && msg.response && (
              <>
                {msg.response.used_fallback && (
                  <span className={styles.fallbackBadge}>(AI narration unavailable)</span>
                )}
                <StructuredResponseBlock
                  queryType={msg.response.query_type}
                  engineData={msg.response.structured_data.engine_data}
                  partial={msg.response.structured_data.partial}
                  error={msg.response.structured_data.error}
                  onExampleClick={handleSubmit}
                />
              </>
            )}
          </div>
        ))}

        {isLoading && (
          <div className={styles.loadingRow}>
            <span>xgGaffer is thinking...</span>
          </div>
        )}
      </div>

      {inputError && <p className={styles.inputError}>{inputError}</p>}

      <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
}