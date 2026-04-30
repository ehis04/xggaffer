import { useEffect, useRef, useState } from 'react';

import { chatQuery } from '../../../services/api/predictionsApi';
import type { ChatResponse } from '../../../types/prediction';
import type { ApiEnvelope } from '../../../common/types/response';
import type { FileAttachmentData } from '../FileAttachment';
import type { PinnedOutput } from '../PinnedOutputsPanel';
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
  onMessagesChange?: (messages: Array<{ role: string; content: string }>) => void;
  onPin?: (output: PinnedOutput) => void;
  attachment?: FileAttachmentData | null;
  onAttachmentUsed?: () => void;
}

export default function ChatInterface({
  starterQueries,
  onMessagesChange,
  onPin,
  attachment,
  onAttachmentUsed,
}: ChatInterfaceProps) {
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
    let fullQuery = query;
    let imageB64: string | undefined;
    let imageMediaType: string | undefined;

    if (attachment) {
      if (attachment.type === 'image') {
        imageB64 = attachment.content;
        imageMediaType = attachment.media_type;
      } else {
        fullQuery = `${query}\n\n${attachment.context_text}`;
      }
      onAttachmentUsed?.();
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
    };

    const next = [...messages, userMessage];
    setMessages(next);
    onMessagesChange?.(next.map(m => ({ role: m.role, content: m.content })));
    setIsLoading(true);
    setInputError(null);

    try {
      const envelope = await chatQuery(fullQuery, imageB64, imageMediaType);
      const chatData = envelope.data;
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: chatData?.prose ?? '',
        envelope,
      };
      const withAssistant = [...next, assistantMessage];
      setMessages(withAssistant);
      onMessagesChange?.(withAssistant.map(m => ({ role: m.role, content: m.content })));
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
            {activeStarters.map(q => (
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

        {messages.map((msg, idx) => {
          const chatData = msg.envelope?.data ?? null;
          const sourceCoverage = (chatData?.structured_data?.engine_data as Record<string, unknown> | undefined)?.source_coverage as
            | { used_sources?: string[]; coverage_status?: string }
            | undefined;
          return (
            <div
              key={msg.id}
              className={msg.role === 'user' ? styles.userMessage : styles.assistantMessage}
            >
              {msg.role === 'assistant' && onPin && (
                <div className={styles.msgPinRow}>
                  <button
                    className={styles.msgPinBtn}
                    aria-label="Pin this response"
                    title="Pin question and response"
                    onClick={() => {
                      const question = messages[idx - 1]?.content ?? '';
                      onPin({
                        id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
                        label: question
                          ? question.slice(0, 60) + (question.length > 60 ? '\u2026' : '')
                          : chatData?.query_type ?? 'Pinned response',
                        query_type: chatData?.query_type ?? 'RESPONSE',
                        data: (chatData?.structured_data?.engine_data as Record<string, unknown>) ?? {},
                        question,
                        prose: msg.content,
                        pinned_at: new Date().toISOString(),
                      });
                    }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                      <path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5v6h2v-6h5v-2l-2-2z" />
                    </svg>
                    Pin
                  </button>
                </div>
              )}
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
                  {sourceCoverage?.used_sources && sourceCoverage.used_sources.length > 0 && (
                    <span className={styles.fallbackBadge}>
                      Sources: {sourceCoverage.used_sources.join(', ')} ({sourceCoverage.coverage_status ?? 'partial'})
                    </span>
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