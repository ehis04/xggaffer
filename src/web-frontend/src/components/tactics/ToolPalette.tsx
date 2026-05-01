import React from 'react';
import type { TacticsActiveTool } from '../../types/tactics';
import styles from './ToolPalette.module.css';

interface ToolOption {
  value: TacticsActiveTool;
  label: string;
}

interface ToolPaletteProps {
  activeTool: TacticsActiveTool;
  onSelectTool: (tool: TacticsActiveTool) => void;
}

const TOOL_OPTIONS: ToolOption[] = [
  { value: 'select', label: 'Select' },
  { value: 'ball', label: 'Ball' },
  { value: 'arrow', label: 'Arrow' },
  { value: 'line', label: 'Line' },
  { value: 'zone', label: 'Zone' },
  { value: 'text', label: 'Text' },
];

const ToolPalette: React.FC<ToolPaletteProps> = ({
  activeTool,
  onSelectTool,
}) => {
  return (
    <section aria-label="Drawing tools" className={styles.palette}>
      <span className={styles.label}>
        Tools
      </span>

      <div className={styles.toolRow}>
        {TOOL_OPTIONS.map((tool) => {
          const isActive = tool.value === activeTool;

          return (
            <button
              key={tool.value}
              type="button"
              onClick={() => onSelectTool(tool.value)}
              aria-pressed={isActive}
              className={isActive ? `${styles.toolButton} ${styles.toolButtonActive}` : styles.toolButton}
            >
              {tool.label}
            </button>
          );
        })}
      </div>
    </section>
  );
};

export default ToolPalette;