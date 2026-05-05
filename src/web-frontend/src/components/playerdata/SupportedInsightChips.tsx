import React from 'react';
import type { SupportedInsightIntent, SupportedInsightOption } from './SupportedInsightChips.types';
import { DEFAULT_SUPPORTED_INSIGHT_OPTIONS } from './SupportedInsightChips.types';

interface SupportedInsightChipsProps {
  options?: SupportedInsightOption[];
  selectedIntent: SupportedInsightIntent;
  onSelect: (intent: SupportedInsightIntent) => void;
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
  showHelperText?: boolean;
}

const containerStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '0.6rem',
};

const chipBaseStyle: React.CSSProperties = {
  borderRadius: '999px',
  border: '1px solid rgba(255,255,255,0.14)',
  background: 'transparent',
  color: 'inherit',
  padding: '0.6rem 0.95rem',
  cursor: 'pointer',
  fontSize: '0.92rem',
  lineHeight: 1.2,
  transition: 'background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease',
};

const chipSelectedStyle: React.CSSProperties = {
  ...chipBaseStyle,
  border: '1px solid rgba(255,255,255,0.28)',
  background: 'rgba(255,255,255,0.08)',
  fontWeight: 600,
};

const chipDisabledStyle: React.CSSProperties = {
  ...chipBaseStyle,
  opacity: 0.45,
  cursor: 'not-allowed',
};

const helperTextStyle: React.CSSProperties = {
  marginTop: '0.35rem',
  fontSize: '0.78rem',
  opacity: 0.72,
};

const SupportedInsightChips: React.FC<SupportedInsightChipsProps> = ({
  options = DEFAULT_SUPPORTED_INSIGHT_OPTIONS,
  selectedIntent,
  onSelect,
  disabled = false,
  className,
  ariaLabel = 'Supported insight actions',
  showHelperText = false,
}) => {
  const handleSelect = (intent: SupportedInsightIntent, isDisabled: boolean) => {
    if (disabled || isDisabled) {
      return;
    }

    onSelect(intent);
  };

  return (
    <div
      className={className}
      style={containerStyle}
      role="group"
      aria-label={ariaLabel}
    >
      {options.map((option) => {
        const isSelected = option.intent === selectedIntent;
        const isDisabled = disabled || Boolean(option.disabled);

        const buttonStyle = isDisabled
          ? chipDisabledStyle
          : isSelected
          ? chipSelectedStyle
          : chipBaseStyle;

        return (
          <button
            key={option.intent}
            type="button"
            style={buttonStyle}
            onClick={() => handleSelect(option.intent, isDisabled)}
            aria-pressed={isSelected}
            disabled={isDisabled}
            title={option.helperText || option.label}
          >
            <span>{option.label}</span>
            {showHelperText && option.helperText ? (
              <div style={helperTextStyle}>{option.helperText}</div>
            ) : null}
          </button>
        );
      })}
    </div>
  );
};

export default SupportedInsightChips;