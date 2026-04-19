import { useState, useEffect, useRef } from "react";
import ChatInterface from "./ChatInterface";
import "./css/ChatPopUp.css";

export default function ChatPopUp() {
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isOpen) setIsOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  return (
    <>
      {isOpen && (
        <div
          className="chat-pu-backdrop"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}

      <div
        ref={panelRef}
        className={`chat-pu-panel ${isOpen ? "chat-pu-panel--open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label="xgGaffer chat"
      >
        <div className="chat-pu-panel-header">
          <div className="chat-pu-panel-title">
            <span className="chat-pu-panel-dot" />
            <span>xgGaffer</span>
            <span className="chat-pu-panel-sub">
              Ask anything about football anlytics
            </span>
          </div>
          <button
            className="chat-pu-panel-close"
            onClick={() => setIsOpen(false)}
            aria-label="Close xgGaffer"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M1 1l12 12M13 1L1 13"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        <div className="chat-pu-panel-body">{isOpen && <ChatInterface />}</div>
      </div>

      <button
        className={`chat-pu-fab ${isOpen ? "chat-pu-fab--hidden" : ""}`}
        onClick={() => setIsOpen(true)}
        aria-label="Open xgGaffer predictions chat"
        title="xgGaffer"
      >
        <svg
          width="26"
          height="26"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          <path d="M8 10h.01M12 10h.01M16 10h.01" />
        </svg>
        <span className="chat-pu-fab-label">xgGaffer</span>
      </button>
    </>
  );
}
