import React from 'react';
import type { TacticsActiveTool } from '../../types/tactics';

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
    <section
      aria-label="Drawing tools"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '10px',
        alignItems: 'center',
        padding: '14px 16px',
        marginBottom: '16px',
        border: '1px solid #d1d5db',
        borderRadius: '14px',
      }}
    >
      <span
        style={{
          fontWeight: 700,
          minWidth: 'fit-content',
        }}
      >
        Tools
      </span>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        {TOOL_OPTIONS.map((tool) => {
          const isActive = tool.value === activeTool;

          return (
            <button
              key={tool.value}
              type="button"
              onClick={() => onSelectTool(tool.value)}
              aria-pressed={isActive}
              style={{
                padding: '8px 12px',
                borderRadius: '999px',
                border: isActive ? '1px solid #111827' : '1px solid #9ca3af',
                background: isActive ? '#111827' : '#ffffff',
                color: isActive ? '#ffffff' : '#111827',
                fontWeight: 600,
                cursor: 'pointer',
              }}
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