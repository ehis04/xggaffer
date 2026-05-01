import React, { useEffect, useState } from 'react';
import type {
  TacticsNonPlayerItem,
  UpdateTacticsBoardItemPayload,
} from '../../types/tactics';
import styles from './ObjectProperties.module.css';

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
      <div className={styles.emptyCard}>
        <p className={styles.emptyText}>
          This item has no editable properties in Phase D.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      {supportsLabel ? (
        <label className={styles.field}>
          <span className={styles.label}>Text label</span>
          <input
            type="text"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            disabled={isSubmitting}
            maxLength={40}
            className={styles.input}
          />
        </label>
      ) : null}

      {supportsRotation ? (
        <label className={styles.field}>
          <span className={styles.label}>Rotation</span>
          <input
            type="number"
            value={rotation}
            onChange={(event) => setRotation(event.target.value)}
            disabled={isSubmitting}
            step="1"
            className={styles.input}
          />
        </label>
      ) : null}

      {supportsDimensions ? (
        <div className={styles.dimensionGrid}>
          <label className={styles.field}>
            <span className={styles.label}>Width</span>
            <input
              type="number"
              value={width}
              onChange={(event) => setWidth(event.target.value)}
              disabled={isSubmitting}
              min="0.1"
              step="0.1"
              className={styles.input}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>Height</span>
            <input
              type="number"
              value={height}
              onChange={(event) => setHeight(event.target.value)}
              disabled={isSubmitting}
              min="0.1"
              step="0.1"
              className={styles.input}
            />
          </label>
        </div>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className={styles.submitButton}
      >
        {isSubmitting ? 'Updating...' : 'Apply'}
      </button>
    </form>
  );
};

export default ObjectProperties;