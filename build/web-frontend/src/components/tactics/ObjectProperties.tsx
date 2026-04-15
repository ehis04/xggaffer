import React, { useEffect, useState } from 'react';
import type {
  TacticsNonPlayerItem,
  UpdateTacticsBoardItemPayload,
} from '../../types/tactics';

interface ObjectPropertiesProps {
  item: TacticsNonPlayerItem;
  isSubmitting: boolean;
  onApplyProperties: (payload: UpdateTacticsBoardItemPayload) => void;
}

const parseNumberWithFallback = (value: string, fallback: number): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const ObjectProperties: React.FC<ObjectPropertiesProps> = ({
  item,
  isSubmitting,
  onApplyProperties,
}) => {
  const [label, setLabel] = useState(item.item_type === 'text' ? item.label : '');
  const [rotation, setRotation] = useState(String(item.rotation));
  const [width, setWidth] = useState(item.item_type === 'zone' ? String(item.width) : '');
  const [height, setHeight] = useState(item.item_type === 'zone' ? String(item.height) : '');

  useEffect(() => {
    setLabel(item.item_type === 'text' ? item.label : '');
    setRotation(String(item.rotation));
    setWidth(item.item_type === 'zone' ? String(item.width) : '');
    setHeight(item.item_type === 'zone' ? String(item.height) : '');
  }, [item]);

  const supportsLabel = item.item_type === 'text';
  const supportsRotation =
    item.item_type === 'text' ||
    item.item_type === 'arrow' ||
    item.item_type === 'line' ||
    item.item_type === 'zone';
  const supportsDimensions = item.item_type === 'zone';

  const hasEditableFields = supportsLabel || supportsRotation || supportsDimensions;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();

    const payload: UpdateTacticsBoardItemPayload = {};

    if (supportsLabel) {
      const nextLabel = label.trim();
      if (!nextLabel) {
        return;
      }
      payload.label = nextLabel;
    }

    if (supportsRotation) {
      payload.rotation = parseNumberWithFallback(rotation, item.rotation);
    }

    if (supportsDimensions) {
      const nextWidth = Math.max(0.1, parseNumberWithFallback(width, item.width));
      const nextHeight = Math.max(0.1, parseNumberWithFallback(height, item.height));
      payload.width = nextWidth;
      payload.height = nextHeight;
    }

    onApplyProperties(payload);
  };

  if (!hasEditableFields) {
    return (
      <div
        style={{
          marginTop: '12px',
          padding: '12px',
          border: '1px solid #d1d5db',
          borderRadius: '10px',
        }}
      >
        <p style={{ margin: 0 }}>
          This item has no editable properties in Phase D.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        display: 'grid',
        gap: '12px',
        marginTop: '12px',
      }}
    >
      {supportsLabel ? (
        <label style={{ display: 'grid', gap: '6px' }}>
          <span style={{ fontWeight: 600 }}>Text label</span>
          <input
            type="text"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            disabled={isSubmitting}
            maxLength={40}
            style={{
              padding: '8px 10px',
              borderRadius: '8px',
              border: '1px solid #9ca3af',
            }}
          />
        </label>
      ) : null}

      {supportsRotation ? (
        <label style={{ display: 'grid', gap: '6px' }}>
          <span style={{ fontWeight: 600 }}>Rotation</span>
          <input
            type="number"
            value={rotation}
            onChange={(event) => setRotation(event.target.value)}
            disabled={isSubmitting}
            step="1"
            style={{
              padding: '8px 10px',
              borderRadius: '8px',
              border: '1px solid #9ca3af',
            }}
          />
        </label>
      ) : null}

      {supportsDimensions ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '10px',
          }}
        >
          <label style={{ display: 'grid', gap: '6px' }}>
            <span style={{ fontWeight: 600 }}>Width</span>
            <input
              type="number"
              value={width}
              onChange={(event) => setWidth(event.target.value)}
              disabled={isSubmitting}
              min="0.1"
              step="0.1"
              style={{
                padding: '8px 10px',
                borderRadius: '8px',
                border: '1px solid #9ca3af',
              }}
            />
          </label>

          <label style={{ display: 'grid', gap: '6px' }}>
            <span style={{ fontWeight: 600 }}>Height</span>
            <input
              type="number"
              value={height}
              onChange={(event) => setHeight(event.target.value)}
              disabled={isSubmitting}
              min="0.1"
              step="0.1"
              style={{
                padding: '8px 10px',
                borderRadius: '8px',
                border: '1px solid #9ca3af',
              }}
            />
          </label>
        </div>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        style={{
          justifySelf: 'start',
          padding: '9px 14px',
          borderRadius: '999px',
          border: '1px solid #111827',
          background: '#111827',
          color: '#ffffff',
          fontWeight: 600,
          cursor: isSubmitting ? 'default' : 'pointer',
        }}
      >
        {isSubmitting ? 'Updating...' : 'Apply'}
      </button>
    </form>
  );
};

export default ObjectProperties;