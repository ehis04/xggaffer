import { useEffect, useRef, useState } from 'react';

import { chatQuery } from '../../../services/api/predictionsApi';
import type { ChatResponse } from '../../../types/prediction';
import type { ApiEnvelope } from '../../../common/types/response';
import { FreshnessBadge } from '../../../common/components/FreshnessBadge';
import ChatInput from './ChatInput';
import StructuredResponseBlock from './StructuredResponseBlock';
import styles from './css/ChatInterface.module.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  envelope?: ApiEnvelope<ChatResponse>;
}

const STARTER_QUERIES = [
  'Compare Arsenal vs Chelsea with bookmaker odds',
  'What is xG?',
  'Show me the market view for Liverpool vs Man City',
  'What lineup will Arsenal use?',
] as const;

interface ChatInterfaceProps {
  starterQueries?: readonly string[];
}

export default function ChatInterface({ starterQueries }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [inputError, setInputError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const activeStarters = starterQueries ?? STARTER_QUERIES;

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
      const envelope = await chatQuery(query);
      const chatData = envelope.data;
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: chatData?.prose ?? '',
        envelope,
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
            {activeStarters.map((q) => (
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

        {messages.map((msg) => {
          const chatData = msg.envelope?.data ?? null;
          return (
            <div
              key={msg.id}
              className={msg.role === 'user' ? styles.userMessage : styles.assistantMessage}
            >
              <p className={styles.messageText}>{msg.content}</p>
              {msg.role === 'assistant' && msg.envelope && (
                <>
                  <FreshnessBadge freshness={msg.envelope.freshness} />
                  {chatData?.used_fallback && (
                    <span className={styles.fallbackBadge}>(AI narration unavailable)</span>
                  )}
                  {chatData && (
                    <StructuredResponseBlock
                      queryType={chatData.query_type}
                      engineData={chatData.structured_data.engine_data}
                      partial={chatData.structured_data.partial}
                      error={chatData.structured_data.error}
                      onExampleClick={handleSubmit}
                    />
                  )}
                </>
              )}
            </div>
          );
        })}

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