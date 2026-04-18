import React from 'react';
import { Link } from 'react-router-dom';

export interface InsightResponseAction {
  label: string;
  to?: string;
  onClick?: () => void;
}

export interface InsightResponseBlockData {
  title: string;
  body: string;
  bullets?: string[];
  meta?: string[];
  action?: InsightResponseAction;
  isUnavailable?: boolean;
}

interface InsightResponseBlockProps {
  response: InsightResponseBlockData | null;
  isLoading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  className?: string;
}

const containerStyle: React.CSSProperties = {
  marginTop: '1rem',
  borderRadius: '14px',
  padding: '0.95rem',
  background: 'rgba(255,255,255,0.035)',
  border: '1px solid rgba(255,255,255,0.1)',
};

const titleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '1rem',
  fontWeight: 700,
};

const bodyStyle: React.CSSProperties = {
  margin: '0.55rem 0 0 0',
  lineHeight: 1.55,
};

const listStyle: React.CSSProperties = {
  margin: '0.8rem 0 0 1rem',
  padding: 0,
};

const listItemStyle: React.CSSProperties = {
  marginBottom: '0.35rem',
  lineHeight: 1.45,
};

const metaRowStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '0.5rem',
  marginTop: '0.85rem',
};

const metaPillStyle: React.CSSProperties = {
  fontSize: '0.82rem',
  borderRadius: '999px',
  padding: '0.3rem 0.6rem',
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
};

const stateStyle: React.CSSProperties = {
  ...containerStyle,
  opacity: 0.9,
};

const unavailableStyle: React.CSSProperties = {
  ...containerStyle,
  border: '1px solid rgba(255,255,255,0.08)',
  background: 'rgba(255,255,255,0.02)',
};

const actionStyle: React.CSSProperties = {
  display: 'inline-flex',
  marginTop: '0.9rem',
  textDecoration: 'none',
  borderRadius: '10px',
  padding: '0.65rem 0.95rem',
  border: '1px solid rgba(255,255,255,0.14)',
  background: 'rgba(255,255,255,0.06)',
  color: 'inherit',
  fontWeight: 600,
  cursor: 'pointer',
};

const buttonResetStyle: React.CSSProperties = {
  ...actionStyle,
  fontFamily: 'inherit',
  fontSize: 'inherit',
};

const InsightResponseBlock: React.FC<InsightResponseBlockProps> = ({
  response,
  isLoading = false,
  error = null,
  emptyMessage = 'No deterministic insight response is available yet.',
  className,
}) => {
  if (isLoading) {
    return (
      <div className={className} style={stateStyle}>
        <h3 style={titleStyle}>Loading insight</h3>
        <p style={bodyStyle}>
          The deterministic insight response is being prepared from stored playerdata.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={className} style={unavailableStyle}>
        <h3 style={titleStyle}>Insight unavailable</h3>
        <p style={bodyStyle}>{error}</p>
      </div>
    );
  }

  if (!response) {
    return (
      <div className={className} style={unavailableStyle}>
        <h3 style={titleStyle}>No insight selected</h3>
        <p style={bodyStyle}>{emptyMessage}</p>
      </div>
    );
  }

  const bullets = response.bullets ?? [];
  const meta = response.meta ?? [];

  return (
    <div
      className={className}
      style={response.isUnavailable ? unavailableStyle : containerStyle}
    >
      <h3 style={titleStyle}>{response.title}</h3>
      <p style={bodyStyle}>{response.body}</p>

      {bullets.length > 0 && (
        <ul style={listStyle}>
          {bullets.map((bullet) => (
            <li key={bullet} style={listItemStyle}>
              {bullet}
            </li>
          ))}
        </ul>
      )}

      {meta.length > 0 && (
        <div style={metaRowStyle}>
          {meta.map((item) => (
            <span key={item} style={metaPillStyle}>
              {item}
            </span>
          ))}
        </div>
      )}

      {response.action?.to && response.action.label && (
        <Link to={response.action.to} style={actionStyle}>
          {response.action.label}
        </Link>
      )}

      {!response.action?.to && response.action?.onClick && response.action.label && (
        <button
          type="button"
          onClick={response.action.onClick}
          style={buttonResetStyle}
        >
          {response.action.label}
        </button>
      )}
    </div>
  );
};

export default InsightResponseBlock;